import argparse
import time

import human36m
import numpy as np
import model
import torch.optim as optim
import torch
import torch.nn as nn
import torch.nn.functional as F
from utils import data_transforms
from torchvision import transforms
from torch.autograd import Variable

# Arguments
parser = argparse.ArgumentParser(description="PyTorch Human3.6M Training")
parser.add_argument("data", metavar="DIR", help="Path to HDF5 file")
parser.add_argument("--epochs", default=10, type=int, metavar="N",
        help="Number of total epochs to run")
parser.add_argument("--start-epoch", default=0, type=int, metavar="N",
        help="Manual epoch number (useful on restarts)")
parser.add_argument("-b", "--batch-size", default=1, type=int, metavar="N",
        help="Mini-batch size (default: 1)")
parser.add_argument("-lr", "--learning-rate", default=1e-3, type=float,
        metavar="LR", help="Initial learning rate")
parser.add_argument("--momentum", default=0.9, type=float, metavar="M",
        help="Momentum (default: 0.9)")
parser.add_argument("--print-freq", "-p", default=10, type=int, metavar="N",
        help="Print frequency (default: 10)")

def main():
    global args
    args = parser.parse_args()

    torch.cuda.manual_seed(1)

    m = model.DeepPose()
    m.cuda()

    print("Loading data...")
    a = human36m.HUMAN36MPose(args.data, transform=data_transforms.Compose([
            data_transforms.RandomCrop(220),
            data_transforms.ToTensor(),
            data_transforms.Normalize(
                mean=[0.00094127, 0.00060294, 0.0005603],
                std=[0.02102633, 0.01346872, 0.01251619]
            )
        ]))

    train_loader = torch.utils.data.DataLoader(a, batch_size=args.batch_size,
            shuffle=True)

    # Define loss function and optimizer
    criterion = nn.MSELoss().cuda()
    optimizer = torch.optim.SGD(m.parameters(), args.learning_rate,
            momentum=args.momentum)

    print("Starting \"training\"")
    for epoch in range(args.start_epoch, args.epochs):
        # train
        train(train_loader, m, criterion, optimizer, epoch)

def train(train_loader, model, criterion, optimizer, epoch):
    batch_time = AverageMeter()
    data_time = AverageMeter()
    losses = AverageMeter()
    mpjpe = AverageMeter()

    # Switch to train mode
    model.train()

    end = time.time()
    for batch_idx, (input, target) in enumerate(train_loader):
        # Measure data loading time
        data_time.update(time.time() - end)

        input = input.cuda()
        target = target.cuda()
        input_var, target_var = Variable(input), Variable(target)

        # Compute output
        output = model(input_var)
        loss = criterion(output, target_var)

        # Record loss
        acc = accuracy(output.data, target)
        losses.update(loss.data[0], input.size(0))
        mpjpe.update(acc)

        # Compute gradient and run optimizer
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        # Record elapsed time
        batch_time.update(time.time() - end)
        end = time.time()

        if batch_idx % args.print_freq == 0:
            print('Epoch: {0} [{1}/{2}]\t'
                  'Time {batch_time.val:.3f} ({batch_time.avg:.3f})\t'
                  'Loss {loss.val:.4f} ({loss.avg:.4f})\t'
                  'MPJPE {acc.val:.4f} ({acc.avg:.4f})\t'.format(
                epoch, batch_idx, len(train_loader),
                batch_time=batch_time, data_time=data_time, loss=losses,
                acc=mpjpe))

def accuracy(output, target):
    """Computes mean per joint position error (MPJPE)
    TODO: Do not hardcode values
    """
    batch_size = target.size(0)

    v = 0
    for i in range(batch_size):
        o = output[i].view(32, 2)
        t = target[i].view(32, 2)
        d = o - t
        s = 0
        for j in range(32):
            d_norm = d[j].norm()
            s += d_norm
        s /= 32
        v += s

    v /= batch_size
    return v

class AverageMeter(object):
    """Computes and stores the average and current value"""
    def __init__(self):
        self.reset()

    def reset(self):
        self.val = 0
        self.avg = 0
        self.sum = 0
        self.count = 0

    def update(self, val, n=1):
        self.val = val
        self.sum += val * n
        self.count += n
        self.avg = self.sum / self.count

if __name__ == "__main__":
    main()
