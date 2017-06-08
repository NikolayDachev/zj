#!/usr/bin/env python2.7
########################################################################################
# zj license information
#
'''
Copyright (c) <2017>, <Nikolay Georgiev Dachev> <nikolay@dachev.info>
All rights reserved.
Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:
1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.
3. Neither the name of the copyright holder nor the names of its contributors may be used to endorse or promote products derived from this software without specific prior written permission.
THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES,
INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY,
OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
 LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
 OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
'''


from datetime import datetime
from tabulate import tabulate
import logging
import subprocess
import os
import sys
import cmd
import argparse

########################################################################################
# Main config vars:
########################################################################################

# jadm version
_zj_version = "ver. 1.0.0"

# jail.conf location by default /etc/jail.conf
_jailconf = '/etc/jail.conf'

# jadm log file
_logfile = '/var/log/zj.log'

# network config

# vnet
vnet = [
'### network settings ###',
'vnet;',
'vnet.interface = "epair${jid}b";',
'exec.start = "ifconfig lo0 127.0.0.1/8";',
'exec.prestart = "ifconfig epair${jid} create";',
'exec.prestart += "ifconfig $bridge addm epair${jid}a up";',
'exec.prestart += "ifconfig epair${jid}a up";',
'exec.start += "ifconfig epair${jid}b $jip";',
'exec.start += "route add default $jgw";',
'exec.start += "/bin/sh /etc/rc";',
'exec.poststop = "ifconfig $bridge deletem epair${jid}a";',
'exec.poststop += "ifconfig epair${jid}a destroy";',
'exec.stop = "/bin/sh /etc/rc.shutdown";',
'exec.clean;',
'persist;'
]

dhcp = [
'### network settings ###',
'vnet;',
'vnet.interface = "epair${jid}b";',
'exec.start = "ifconfig lo0 127.0.0.1/8";',
'exec.prestart = "ifconfig epair${jid} create";',
'exec.prestart += "ifconfig $bridge addm epair${jid}a up";',
'exec.prestart += "ifconfig epair${jid}a up";',
'exec.start += "dhclient epair${jid}b";',
'exec.start += "/bin/sh /etc/rc";',
'exec.poststop = "ifconfig $bridge deletem epair${jid}a";',
'exec.poststop += "ifconfig epair${jid}a destroy";',
'exec.stop = "/bin/sh /etc/rc.shutdown";',
'exec.clean;',
'persist;'
]

# no vnet
net = [
'### network settings ###',
'ip4.addr = "$jip";',
'exec.start = "/bin/sh /etc/rc";',
'exec.stop = "/bin/sh /etc/rc.shutdown";',
'persist;',
]

# nfs fstab settings
remnfs = 'nfs rw,hard,intr,bg,rsize=8192,wsize=8192,tcp 0 0'

########################################################################################
# Main Functions
########################################################################################

def log(ltype, msg, logit = None):
   """
########################################################################################
# print msg and log it if is needed
# log([0 - INFO, 1 = WARRNING and 2 - ERROR], 'log message', 'eny value if you want
#      to log in jailog file'
#
   """

   logtype = ['INFO', 'WARNING', 'ERROR']
   print "	%s: %s" % (logtype[ltype], msg)

   if logit != None:
      logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s', level=logging.DEBUG, filename=_logfile)
      if ltype == 0:
         logging.info(msg)
      if ltype == 1:
         logging.warning(msg)
      if ltype == 2:
         logging.error(msg)

class zfs_config:
    def __init__(self):
        # check for zfs.ko
        try:
            subprocess.check_output("kldstat -m zfs", shell=True, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            log(2, "zfs: %s" % e, 1)
            return False

        # check curent zfs dataset
        self.zfs_dataset = {}
        self.zfs_name = subprocess.check_output("zfs list -H -o name", shell=True)
        self.zfs_name = self.zfs_name.split('\n')
        self.zfs_name.remove('')
        for z in self.zfs_name:
            zmount_point = subprocess.check_output("zfs list -H -o mountpoint %s" % z, shell=True).strip()
            zquota = subprocess.check_output("zfs list -H -o quota %s" % z, shell=True).strip()
            zused = subprocess.check_output("zfs list -H -o used %s" % z, shell=True).strip()
            zavai = subprocess.check_output("zfs list -H -o available %s" % z, shell=True).strip()
            zsnaps = 'none'
            try:
               zs = subprocess.check_output("zfs list -t snapshot -H -o name |grep %s@" % z, shell=True).strip()
               zsnaps = zs.split('\n')
            except:
               pass
            self.zfs_dataset[z] = {'zfs': z, 'path': zmount_point, 'quota': zquota, 'snapshots': zsnaps, 'ua':[zused, zavai]}

    def get(self, name = None):
        if name == None:
            return self.zfs_dataset
        if name not in self.zfs_dataset.keys():
            return False
        return self.zfs_dataset[name]

    def create(self, name, path, quota):
        pass

    def remove(self, name):
        pass

    def quota(self, name, quota):
        pass

    def rename(self, name, newname):
        pass

    def snapshot(self, name):
        pass

class table:
     def __init__(self, arg):
         self.arg = arg

     def show(self):

         # table menu
         lmen = ["FLAGS", "ACTIVE", "JID", "NAME", "HOSTNAME",
                 "IP ADDRESS", "GATEWAY", "PATH", "ZUSED/ZAVAIL", "ZQUOTA",  "ZSNAP"]
         # check if we use short list - jls
         if self.arg[0] == 'jls':
              lmen = ["FLAGS", "ACTIVE", "JID", "NAME", "HOSTNAME", "IP ADDRESS"]


         # search before display
         if len(self.arg) > 1:
            self.jlist = self.search()
            if self.jlist == False:
               return False

         self.jlist = []
         # sorte list by x[2] - jid
         self.jlist = sorted(self.jlist, key=lambda x: x[2])
         # print table
         print tabulate(self.jlist, lmen)

class lcmd(cmd.Cmd):
     """
     ########################################################################################
     #  interactive main menu with 'cmd' function
     #
     """

     prompt = 'jadm:> '

     local_global = ['remove',  'add']
     snap = ['create',  'remove',  'restore']
     listcmd = ['list', 'name', 'jid','hostname',  'ip',  'gw', 'active', 'dying',
              'vnet', 'zfs', 'skel', 'quota', 'linked', 'used', 'empty', 'no']
     mserver = ['server',  'client']
     archive = ['create',  'restore']

     def emptyline(self):
         pass

     def default(self, line):
         log(2, "'%s' not working, please use 'help' or '-h only for cli'" % line)
         return cmd.Cmd.default(self, line)

     def do_list(self, arg):
         """
   List of jails
   -------------
   -- FLAGS
      S - skeleton model jail
      V - vnet jail
      Z - zfs jail
      _D - dying jail

   -- USAGE: list
      (search options)
      - revers       (usage: list no ... )

      - by name      (usage: list name 'jail name' )
      - by jid       (usage: list jid 'jail id' )
      - by hostname  (usage: list hostname 'jail hostname' )
      - by path      (usage: lisy path '/jail/home/path' )
      - by ipaddress (usage: list ip 'ipaddress' )
      - by gateway   (usage: list gw 'gateway ip' )

      - actvie jails (usage: list active )
      - dying jails  (usage: list dying )
      - vnet jails   (usage: list vnet )
      - skel jails   (usage: list skel )
      - linked jails (usage: list linked )

   -- ZFS JAILS
      - zfs jails (usage: list zfs)
      - by zfs quota (usage: list quota 'xxx('K', 'M', 'G', 'T', 'P', 'E')')
      show jails with quota = or > form x number
      - by zfs used space (usage: list used 'xxx('K', 'M', 'G', 'T', 'P', 'E')')
      show jails with used space = or > form x number
         """
         arg = str(arg).split(' ')
         arg.insert(0, 'list')

         if arg[0] != '':
            arg = [i for i in arg if i != '']

         t = table(arg)
         t.show()

     def do_jls(self, arg):
         """
   List of jails in short format
   -----------------------------
   -- same as 'list'
      check 'help list' for more details
         """
         arg = str(arg).split(' ')
         arg.insert(0, 'jls')

         if arg[0] != '':
             arg = [i for i in arg if i != '']

         t = table(arg)
         t.show()

     def do_exit(self, arg):
         """
   Exit from JADM
   --------------
   -- USAGE: exit
         """
         print "Good bye!"
         sys.exit(0)

     def do_quit(self, arg):
         """
   Exit from JADM
   --------------
   -- USAGE: quit
         """
         print "Good bye!"
         sys.exit(0)

     def complete_list(self, text, line, begidx, endidx):
         if not text:
             completions = self.listcmd[:]
         else:
             completions = [f for f in self.listcmd if f.startswith(text)]
             return completions


########################################################################################
# Start Jadm script
########################################################################################

zfs = zfs_config()

# main menu shell
#welcome()
lcmd().cmdloop()

########################################################################################
# End Jadm script
########################################################################################
