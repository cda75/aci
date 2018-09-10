# -*- coding: utf-8 -*-
'''

Установка зависимостей

1. Установить последнюю версию Python 2.7 с сайта  https://www.python.org/downloads/.
2. Добавить следующие директорию в системную переменную Windows PATH: ;C:\Python27;C:\Python27\Scripts
3. Загрузить пакет PIP с сайта https://bootstrap.pypa.io/get-pip.py и установить его командой: 
		#python get-pip.py
4. Проапгрейдить PIP командой: 
		#python -m pip install --upgrade pip
5. Скачать файлы (2 штуки с расширением .egg) ACI Cobra Python SDK с любого APIC по адресу https://<APIC IP>/cobra/_downloads/
6. Перейти в директорию со скачанными файлами  *.egg и установить их командами:
		#easy_install -Z acicobra-3.2_2o-py2.7.egg
		#easy_install -Z acimodel-3.2_2o-py2.7.egg
7. Выполнить команду:
		#pip install argparse, pandas, xlrd, numpy

8. Данные считываются из файла input.xlsx

'''
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
import pandas as pd
import numpy as np

from cobra.mit.access import MoDirectory
from cobra.mit.session import LoginSession
from cobra.mit.request import ConfigRequest
from cobra.model.fv import Tenant, AEPg, Ap, BD, Ctx, Subnet, RsCtx, RsBd, RsPathAtt, RsDomAtt, RsProv, RsCons, RsIntraEpg
from argparse import ArgumentParser
from ConfigParser import SafeConfigParser


inputFile = 'input.xlsx'
cfgFile = 'config.cfg'

cfg = SafeConfigParser()
cfg.read(cfgFile)
userName = cfg.get('AUTH', 'user')
userPass = cfg.get('AUTH', 'password')
apicUrl = 'https://' + cfg.get('AUTH', 'url')													
TENANT = cfg.get('APIC', 'tenant')
APP = cfg.get('APIC', 'app')
VRF = cfg.get('APIC', 'vrf')
PORTS = cfg.get('APIC', 'ports').split('\n')
DOMAIN = cfg.get('APIC', 'domain')
CONFIG = ConfigRequest()

def arg_parse():
	parser = ArgumentParser(description='Script for creating Bridge Domain in Cisco ACI Fabric')
	parser.add_argument("--vlan_name", "-vName", type=str, dest='vlan_name', help='VLAN Name')
	parser.add_argument("--vlan_number", "-vNum", type=str, dest='vlan_number', help='VLAN Number')
	parser.add_argument("--subnet", "-s", type=str, dest='subnet', help='Subnet Gateway x.x.x.x/xx')
	args = parser.parse_args()
	return args.vlan_name, args.vlan_number, args.subnet


def login(url, name, password):
	session = LoginSession(url, name, password)
	mo = MoDirectory(session)
	try:
		mo.login()
		print '[+] Login successfull'
	except:
		print '[-] Login Error'
		exit(1)
	return mo


#Get Tenant object by Name
def get_tenant(mo, tName):
	tenant = mo.lookupByDn('uni/tn-' + tName)
	if tenant.name == tName:
		return tenant
	else:
		print '[-] Tenant lookup Error'
		exit(1)


#Create BD
def create_BD(tenant, bdName, vNum, vrf, subnet):
	try:
		fvBD = BD(tenant, name=bdName, arpFlood=u'true')
		Subnet(fvBD, ctrl=u'unspecified', ip=subnet, virtual=u'true')
		RsCtx(fvBD, tnFvCtxName=vrf)
		CONFIG.addMo(fvBD)
		print '[+] Bridge Domain %s created successfully' %bdName
	except:
		print '[-] Error creating Bridge Domain'
		exit(1)


#Create EPG
def create_epg(tenant, bdName, vNum, epgName, apName=APP):
	fvAp = Ap(tenant, apName)
	try:
		fvAEPg = AEPg(fvAp, name=epgName)
		RsBd(fvAEPg, tnFvBDName=bdName)
		CONFIG.addMo(fvAEPg)
		print '[+] EPG %s created successfully' %epgName
		return fvAEPg
	except:
		print '[-] Error creating EPG'
		exit(1)


#Attach Domain to EPG
def add_domain_to_epg(mo, dName=DOMAIN, dType='phys'):
	dName = 'uni/' + dType + '-' + dName
	try:
		RsDomAtt(mo, tDn=dName, resImedcy='immediate')
		print '[+] EPG successfully attached to Domain %s' %DOMAIN
		CONFIG.addMo(mo)
	except:
		print '[-] Error attaching EPG to Domain %s' %DOMAIN
		exit(1)


#Attach static port to EPG
def attach_vpc(moEPG, vNum, port):
	vlan = 'vlan-' + vNum
	try:
		fvInt = RsPathAtt(moEPG, tDn=port, encap=vlan, instrImedcy='immediate')
		print '[+] Port successfully attached to EPG'
		CONFIG.addMo(fvInt)
	except:
		print '[-] Error attaching port <%s> to EPG' %port
		exit(1)


#Add contract to EPG
def add_contract(mo, contractType, contractName):
	if contractType.lower() == 'consumed':
		try:
			RsCons(mo, tnVzBrCPName=contractName)
			print '[+] Contract %s successfully attached to EPG as %s' %(contractName, contractType)
			CONFIG.addMo(mo)
			return mo
		except:
			print '[-] Error attaching contract %s to EPG' %contractName
			exit(1)
	if contractType.lower() == 'provided':
		try:
			RsProv(mo, tnVzBrCPName=contractName)
			print '[+] Contract %s successfully attached to EPG as %s' %(contractName, contractType)
			CONFIG.addMo(mo)
			return mo
		except:
			print '[-] Error attaching contract %s to EPG' %contractName
			exit(1)
	if contractType.lower() == 'intra-epg':
		try:
			RsIntraEpg(mo, tnVzBrCPName=contractName)
			print '[+] Contract %s successfully attached to EPG as %s' %(contractName, contractType)
			CONFIG.addMo(mo)
			return mo
		except:
			print '[-] Error attaching contract %s to EPG' %contractName
			exit(1)


def main():

	df = pd.read_excel(inputFile)
	df['VLAN Name'].replace(' ', np.nan, inplace=True)
	df= df.dropna(subset=['VLAN Name'])
	records = df.to_dict(orient='records')
	for record in records:
		if str(record['Provided Contracts']) != 'nan':
			record['Provided Contracts'] = str(record['Provided Contracts']).split(',')
		else:
			record['Provided Contracts'] = None
		if str(record['Consumed Contracts']) != 'nan':
			record['Consumed Contracts'] = str(record['Consumed Contracts']).split(',')
		else:
			record['Consumed Contracts'] = None

	mo = login(apicUrl, userName, userPass)
	tenant = get_tenant(mo, TENANT)
	for record in records:
		bdName = str(record['VLAN Name']) + '-BD'
		vlan_num = str(record['VLAN Number'])
		subnet = str(record['Subnet'])
		epgName = str(record['VLAN Name']) + '-EPG'
		pContracts = record['Provided Contracts']
		cContracts = record['Consumed Contracts']
		create_BD(tenant, bdName, vlan_num, VRF, subnet)
		EPG = create_epg(tenant, bdName, vlan_num, epgName)
		for port in PORTS:
			attach_vpc(EPG, vlan_num, port)
		add_domain_to_epg(EPG)
		if pContracts:
			for contract in pContracts:
				add_contract(EPG, contractType='provided', contractName=contract)
		if cContracts:
			for contract in cContracts:
				add_contract(EPG, contractType='consumed', contractName=contract)
		mo.commit(CONFIG)


	

if __name__ == '__main__':
	main()

