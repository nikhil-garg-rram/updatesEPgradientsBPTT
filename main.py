import argparse
import torchvision.datasets as datasets
import torchvision.transforms as transforms
import torch.optim as optim
import pickle
import datetime

from netClasses import *
from netFunctions import * 
from plotFunctions import * 

parser = argparse.ArgumentParser(description='Updates of Equilibrium Prop Match Gradients of Backprop Through Time in an RNN with Static Input')
parser.add_argument(
    '--batch-size',
    type=int,
    default=20,
    metavar='N',
    help='input batch size for training (default: 20)')
parser.add_argument(
    '--test-batch-size',
    type=int,
    default=1000,
    metavar='N',
    help='input batch size for testing (default: 1000)')   
parser.add_argument(
    '--epochs',
    type=int,
    default=1,
    metavar='N',
help='number of epochs to train (default: 1)')    
parser.add_argument(
    '--lr_tab',
    nargs = '+',
    type=float,
    default=[0.05, 0.1],
    metavar='LR',
    help='learning rate (default: [0.05, 0.1])')
parser.add_argument(
    '--size_tab',
    nargs = '+',
    type=int,
    default=[10],
    metavar='ST',
    help='tab of layer sizes (default: [10])')      
parser.add_argument(
    '--dt',
    type=float,
    default=0.2,
    metavar='DT',
    help='time discretization (default: 0.2)') 
parser.add_argument(
    '--T',
    type=int,
    default=100,
    metavar='T',
    help='number of time steps in the forward pass (default: 100)')
parser.add_argument(
    '--Kmax',
    type=int,
    default=25,
    metavar='Kmax',
    help='number of time steps in the backward pass (default: 25)')  
parser.add_argument(
    '--beta',
    type=float,
    default=1,
    metavar='BETA',
    help='nudging parameter (default: 1)') 
parser.add_argument(
    '--training-method',
    type=str,
    default='eqprop',
    metavar='TMETHOD',
    help='training method (default: eqprop)')
parser.add_argument(
    '--action',
    type=str,
    default='train',
    help='action to execute (default: train)')    
parser.add_argument(
    '--activation-function',
    type=str,
    default='sigm',
    metavar='ACTFUN',
    help='activation function (default: sigmoid)')
parser.add_argument(
    '--no-clamp',
    action='store_true',
    default=False,
    help='clamp neurons between 0 and 1 (default: True)')
parser.add_argument(
    '--discrete',
    action='store_true',
    default=False, 
    help='discrete-time dynamics (default: False)')
parser.add_argument(
    '--toymodel',
    action='store_true',
    default=False, 
    help='Implement fully connected toy model (default: False)')                                                    
parser.add_argument(
    '--device-label',
    type=int,
    default=0,
    help='selects cuda device (default 0, -1 to select )')
parser.add_argument(
    '--C_tab',
    nargs = '+',
    type=int,
    default=[],
    metavar='LR',
    help='channel tab (default: [])')
parser.add_argument(
    '--padding',
    type=int,
    default=0,
    metavar='P',
    help='padding (default: 0)')
parser.add_argument(
    '--Fconv',
    type=int,
    default=5,
    metavar='F',
    help='convolution filter size (default: 5)')
parser.add_argument(
    '--Fpool',
    type=int,
    default=2,
    metavar='Fp',
    help='pooling filter size (default: 2)')         
parser.add_argument(
    '--benchmark',
    action='store_true',
    default=False, 
    help='benchmark EP wrt BPTT (default: False)')

args = parser.parse_args()

args.conv = not not args.C_tab

batch_size = args.batch_size
batch_size_test = args.test_batch_size

class ReshapeTransform:
    def __init__(self, new_size):
        self.new_size = new_size

    def __call__(self, img):
        return torch.reshape(img, self.new_size)
        
        
class ReshapeTransformTarget:
    def __init__(self, number_classes):
        self.number_classes = number_classes
    
    def __call__(self, target):
        target=torch.tensor(target).unsqueeze(0).unsqueeze(1)
        target_onehot = torch.zeros((1,self.number_classes))      
        return target_onehot.scatter_(1, target, 1).squeeze(0)


if (args.conv):
    transforms=[torchvision.transforms.ToTensor()]
else:
    transforms=[torchvision.transforms.ToTensor(),ReshapeTransform((-1,))]


train_loader = torch.utils.data.DataLoader(
torchvision.datasets.MNIST(root='./data', train=True, download=True,
                         transform=torchvision.transforms.Compose(transforms),
                         target_transform=ReshapeTransformTarget(10)),
batch_size = args.batch_size, shuffle=True)

test_loader = torch.utils.data.DataLoader(
torchvision.datasets.MNIST(root='./data', train=False, download=True,
                         transform=torchvision.transforms.Compose(transforms),
                         target_transform=ReshapeTransformTarget(10)),
batch_size = args.test_batch_size, shuffle=True)



if  args.activation_function == 'sigm':
    def rho(x):
        return 1/(1+torch.exp(-(4*(x-0.5))))
    def rhop(x):
        return 4*torch.mul(rho(x), 1 -rho(x))

elif args.activation_function == 'hardsigm':
    def rho(x):
        return x.clamp(min = 0).clamp(max = 1)
    def rhop(x):
        return (x >= 0) & (x <= 1)

elif args.activation_function == 'tanh':
    def rho(x):
        return torch.tanh(x)
    def rhop(x):
        return 1 - torch.tanh(x)**2 
            
                    
if __name__ == '__main__':
  
    #Build the net

    if args.toymodel:
        net = toyEPcont(args)

    elif (not args.toymodel) & (not args.conv) & (not args.discrete):
        net = EPcont(args)

        if args.benchmark:
            net_bptt = EPcont(args)
            net_bptt.load_state_dict(net.state_dict())

    elif (not args.toymodel) & (not args.conv) & (args.discrete):
        net = EPdisc(args)
        if args.benchmark:
            net_bptt = EPdisc(args)
            net_bptt.load_state_dict(net.state_dict())        

    elif (not args.toymodel) & (args.conv):      
        net = convEP(args)

        if args.benchmark:
            net_bptt = convEP(args)
            net_bptt.load_state_dict(net.state_dict())
        
                                  
    if args.action == 'plotcurves':

        #create path              
        BASE_PATH, name = createPath(args)

        #save hyperparameters
        createHyperparameterfile(BASE_PATH, name, args)

        if (not args.toymodel):
            batch_idx, (data, target) = next(enumerate(train_loader))    
        else:
            data = torch.rand((args.batch_size, net.size_tab[-1]))
            target = torch.zeros((args.batch_size, net.size_tab[0]))
            target[np.arange(args.batch_size), np.random.randint(net.size_tab[0], size = (1,))] = 1
                  
        if net.cuda: 
            data, target = data.to(net.device), target.to(net.device)    

        nS, dS, DT, _ = compute_nSdSDT(net, data, target)
        NT = compute_NT(net, data, target)
        nT, dT = compute_nTdT(NT, DT)
                            
        results_dict = {'nS' : nS, 'dS' : dS, 'NT': NT, 'DT': DT, 
                        'toymodel':args.toymodel}
                          
        outfile = open(os.path.join(BASE_PATH, 'results'), 'wb')
        pickle.dump(results_dict, outfile)
        outfile.close()     
                                                                        
        plt.show()
                                                   
    elif args.action == 'train':

        #create path              
        BASE_PATH, name = createPath(args)

        #save hyperparameters
        createHyperparameterfile(BASE_PATH, name, args)

        #benchmark wrt BPTT
        if args.benchmark:
            error_train_bptt_tab = []
            error_test_bptt_tab = []  

            for epoch in range(1, args.epochs + 1):
                error_train_bptt = train(net_bptt, train_loader, epoch, 'BPTT')		
                error_test_bptt = evaluate(net_bptt, test_loader)
                error_train_bptt_tab.append(error_train_bptt)
                error_test_bptt_tab.append(error_test_bptt)  
                results_dict = {'error_train_bptt_tab' : error_train_bptt_tab, 'error_test_bptt_tab' : error_test_bptt_tab}
                  
                outfile = open(os.path.join(BASE_PATH, 'results'), 'wb')
                pickle.dump(results_dict, outfile)
                outfile.close()  
        
            results_dict_bptt = results_dict
        
        #train with EP
        error_train_tab = []
        error_test_tab = []  

        #*****MEASURE ELAPSED TIME*****#
        start_time = datetime.datetime.now()
        #******************************#
	
        for epoch in range(1, args.epochs + 1):
            error_train = train(net, train_loader, epoch, args.training_method)
            error_test = evaluate(net, test_loader)
            error_train_tab.append(error_train)
            error_test_tab.append(error_test) ;
            results_dict = {'error_train_tab' : error_train_tab, 'error_test_tab' : error_test_tab, 'elapsed_time': datetime.datetime.now() - start_time}  
            if args.benchmark:
                results_dict_bptt.update(results_dict)    
                outfile = open(os.path.join(BASE_PATH, 'results'), 'wb')
                pickle.dump(results_dict_bptt, outfile)
                outfile.close()
            else:   
                outfile = open(os.path.join(BASE_PATH, 'results'), 'wb')
                pickle.dump(results_dict, outfile)
                outfile.close()   



    elif args.action == 'receipe':
        receipe(net, train_loader, 20)
