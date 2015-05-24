import argparse
import subprocess
import os
import struct
import math
import sys

# Number of bytes available for the loader at the beginning of the MBR.
# Kernel command-line arguments follow the loader.
LOADER_SIZE = 314;
# Order of roles within a given disk.
role_order = ["KERNEL", "FILESYS", "SCRATCH", "SWAP"];
role2type = {"KERNEL": 0x20, "FILESYS": 0x21, "SCRATCH": 0x22, "SWAP": 0x23};
type2role = {0x20: "KERNEL", 0x21: "FILESYS", 0x22: "SCRATCH", 0x23: "SWAP"};
parts = {'KERNEL': {'FILE': '/home/adam/research/pintos/src/threads/build/kernel.bin', 'OFFSET': 0, 'BYTES': 84172, 'DISK': 'OUTFILE',
        'START': 0, 'SECTORS':0}};


def diskcreation():
    #KERNEL LOADING
    name = '/home/adam/research/pintos/src/threads/build/kernel.bin';
    #DO SET PARTITION
    #THREE PARTS: 'KERNEL', 'file', name (from above)
    role = 'KERNEL';
    file = 'file';
    f = open(name, "rb");
    mbr = bytearray()
    try:
        mbr = f.read(512)
    finally:
        f.close()
    
    geometry = {'H':16, 'S':63};
    #PYTHON VERSION OF FILEHANDLE THAT SHOULD WORK HERE
    #Will create a new file called makedisk that it will write out to here
    fileopen = open('MAKEDISK', "w");
    loader = read_loader();
    disk = {'KERNEL': parts['KERNEL'], 'DISK': 'MAKEDISK', 'HANDLE': fileopen, 'ALIGN': None, 'GEOMETRY': geometry,
            'FORMAT': 'partitioned', 'LOADER': loader, 'ARGS': ''};
    assemble_disk(disk);


def read_loader():
    name = "/home/adam/research/pintos/src/threads/build/loader.bin";
    handle = open(name, "rb");
    loader = handle.read(LOADER_SIZE);
    return loader;


def assemble_disk(arg={}):
    mygeometry = arg['GEOMETRY'];
    myalign = 0;
    mypad = 0;
    if arg['ALIGN'] == None:
        myalign = 0;
        mypad = 1;
    elif arg['ALIGN'] == 'full':
        myalign = 1;
        mypad = 0;
    elif arg['ALIGN'] == 'none':
        myalign = 0;
        mypad = 0;
    else:
        return null;


    myformat = arg['FORMAT'];


    #Calculate disk size
    mytotalsectors = 0;
    if myformat == 'partitioned':

        if myalign != 0:
            mytotalsectors += mygeometry['S'];
        else:
            mytotalsectors += 1;

    #using role KERNEL here since it is the only thing that we are using
    #for role in role_order:
        myp = arg['KERNEL'];
        mybytes = myp['BYTES'];
        mystart = mytotalsectors;
        myend = mystart + (math.ceil(mybytes / 512.000));
        #cyl_sectors
        numofsectorsincylinderofdisk = mygeometry['H'] * mygeometry['S'];
        if arg['ALIGN'] != None:
            myend = math.ceil(math.ceil(myend / numofsectorsincylinderofdisk) * numofsectorsincylinderofdisk);
        myp['DISK'] = arg['DISK'];
        myp['START'] = mystart;
        myp['SECTORS'] = myend - mystart;
        mytotalsectors = myend;

        #WRITE THE DISK
        mydisk_fn = arg['DISK'];
        mydisk = arg['HANDLE'];
        if myformat == "partitioned" :
            #PACK LOADER INTO MBR
            myloader = arg['LOADER'];
            mymbr = struct.pack("314s", myloader);
            mymbr += make_kernel_command_line(arg['ARGS']);

            #PACK PARTITION TABLE INTO MBR
            #More Padding is required here
            mymbr += make_partition_table(mygeometry, arg);

            #Add signature to MBR.
            mymbr += struct.pack("<H", 0xaa55);

            if len(mymbr) != 512:
                return;

            write_fully(mydisk, mydisk_fn, mymbr);
            if myalign != 0:
                write_zeroes(mydisk, mydisk_fn, 512*(mygeometry['S'] - 1));

        myp = arg['KERNEL'];
        myfn = myp['FILE'];
        mysource = open(myfn, "rb");
        if myp['OFFSET'] > 0:
            mysource.seek(myp['OFFSET']);

        copy_file(mysource, myfn, mydisk, mydisk_fn, myp['BYTES']);

        write_zeroes(mydisk, mydisk_fn, (myp['SECTORS'] * 512 - myp['BYTES']));
    if (mypad != None):
        multiple = mygeometry['H'] * mygeometry['S'];
        div_round_up = int ((math.ceil(mytotalsectors) +  multiple - 1) / multiple);
        round_up = div_round_up * multiple;
        mypad_sectors = round_up;
        write_zeroes(mydisk, mydisk_fn, ((mypad_sectors - mytotalsectors) * 512));





def copy_file(mysource, myfn, mydisk, mydisk_fn, mypbytesvalue):
    myfromhandle = mysource;
    myfromfilename = myfn;
    tohandle = mydisk;
    to_file_name = mydisk_fn;
    size = mypbytesvalue;

    while (size > 0):
        mychunk_size = 4096;
        if mychunk_size > size:
            mychunk_size = size;
        size -= mychunk_size;

        mydata = read_fully(myfromhandle, myfromfilename, mychunk_size);
        write_fully(tohandle, to_file_name, mydata);


def read_fully(myfromhandle, myfromfilename, mychunk_size):
    myhandle = myfromhandle;
    myfile_name = myfromfilename;
    mybytes = mychunk_size;
    myreadbytes = myhandle.read(mychunk_size);
    if myreadbytes == None:
        return;
    if len(myreadbytes) != mybytes:
        print sys.getsizeof(myreadbytes);
        return;
    return myreadbytes;


def write_fully (mydisk, mydisk_fn, mymbr):
    myhandle = mydisk;
    myfile_name = mydisk_fn;
    mydata = mymbr;
    myhandle.write(mydata);


def write_zeroes (mydisk, mydisk_fn, mygeometrychunk):
    myhandle = mydisk;
    myfile_name = mydisk_fn;
    mysize = mygeometrychunk;

    while mysize > 0:
        mychunk_size = 4096;
        if mychunk_size > mysize:
            mychunk_size = mysize
        mysize -= mychunk_size;
        write_fully(myhandle, myfile_name, "\0" * (int(mychunk_size)));



def make_kernel_command_line (arguments):
    argumentstring = '';
    for string in arguments:
        string.replace(' ', '');
        argumentstring += string;
    myargs = sys.getsizeof(arguments);
    if myargs > 128:
        return;
    print len(arguments);
    return struct.pack("<L 128p", len(arguments), argumentstring);

def make_partition_table (geometry, args):
    mygeometry = geometry;
    mypartitions = args;
    mytable = '';
    mybootable = '';
    for role in role_order:
        if (role in mypartitions.keys()):
            myp = mypartitions[role];
            myend = myp['START'] + myp['SECTORS'] - 1;
            if role == 'KERNEL':
                mybootable = 'true';
            if mybootable == 'true':
                mytable += struct.pack("B", 0x80);
            else:
                mytable += struct.pack("B", 0);
            mytable += pack_chs(myp['START'], mygeometry);
            mytable += struct.pack("B", role2type[role]);
            mytable += pack_chs(myend, mygeometry);
            mytable += struct.pack("<L", myp['START']);
            mytable += struct.pack("<L", myp['SECTORS']);
            if len(mytable) % 16 != 0:
                return;
    return struct.pack("64s", mytable);


def pack_chs(startnumber, mygeometrydict):
    mylba = startnumber;
    mygeometry = mygeometrydict;
    #Convert logical sector $lba to 3-byte packed geometrical sector
    myconversionarray = lba_to_chs(mylba, mygeometry);
    mycyl = myconversionarray[0];
    myhead = myconversionarray[1];
    mysect = myconversionarray[2];
    return struct.pack("BBB", myhead, mysect | ((mycyl >> 2) & 0xc0), mycyl & 0xff);


def lba_to_chs(startnumber, mygeometrydict):
    mylba = startnumber;
    mygeometry = mygeometrydict;
    myhpc = mygeometry['H'];
    myspt = mygeometry['S'];

    mycyl =  ( (int)(math.floor(mylba)) / (int)(math.floor((myhpc * myspt))));
    mytemp =  ((int)(math.floor(mylba)) % (int)(math.floor((myhpc * myspt))));
    myhead = (int) ((int)(math.floor(mytemp) / (int)(math.floor(myspt))));
    mysect = ((int) (math.floor(mytemp % myspt + 1)));

    if (mycyl <= 1023):
        return [mycyl, myhead, mysect];
    else:
        return [1023, 254, 63];

diskcreation();


#optional arguments added here
parser = argparse.ArgumentParser(description="Process some args.")
makedisk = 'temp'
parser.add_argument('qemu')

args = parser.parse_args()


args = parser.parse_args()
print args


__author__ = 'adam'
