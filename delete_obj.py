import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from cobra.mit.access import MoDirectory
from cobra.mit.session import LoginSession
from cobra.mit.request import ConfigRequest
from argparse import ArgumentParser
from ConfigParser import SafeConfigParser


cfgFile = 'config.cfg'

cfg = SafeConfigParser()
cfg.read(cfgFile)
userName = cfg.get('AUTH', 'user')
userPass = cfg.get('AUTH', 'password')
apicUrl = 'https://' + cfg.get('AUTH', 'url')
TENANT = cfg.get('APIC', 'tenant')
APP = cfg.get('APIC', 'app')

CONFIG = ConfigRequest()



def arg_parse():
	parser = ArgumentParser(description='Script for deleting objects inside specific Tenant in Cisco ACI Fabric')
	parser.add_argument("--object", "-o", type=str, dest='objType', help='Object type - epg, bd, anp')
	parser.add_argument("--name", "-n", type=str, dest='objName', help='Object name')
	args = parser.parse_args()
	return args.objType, args.objName.split(',')



def main():
	oType, oName = arg_parse()
	session = LoginSession(apicUrl, userName, userPass)
	mo = MoDirectory(session)
	try:
		mo.login()
		print '[+] Login successfull'
	except:
		print '[-] Login Error'
		exit(1)
	
	if ',' in oName:
		oName = oName.split(',')

	tenantDN = 'uni/tn-' + TENANT
	fvTenant = mo.lookupByDn(tenantDN)
	for name in oName:
		if oType.lower() == 'bd':
			dn = tenantDN + '/BD-' + name
		if oType.lower() == 'epg':
			dn = tenantDN + '/ap-' + APP + '/epg-' + name
		if oType == 'ap':
			dn = tenantDN + '/ap-' + name
		obj = mo.lookupByDn(dn)
		if obj:
			try:
				obj.delete()
				print '[+] Object %s "%s" successfully deleted' %(str(oType.upper()), str(name))
				c = ConfigRequest()
				c.addMo(obj)
				mo.commit(c)
			except:
				print '[-] Error deleting object %s "%s"' %(str(oType.upper()), str(name))
				exit(1)
		else:
			print '[-] %s "%s". Error! No such Object! ' %(str(oType.upper()), str(name))
#			exit(1)
		


if __name__ == '__main__':
	main()

