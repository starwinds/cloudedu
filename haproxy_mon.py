#kt cloud autoscaling group과 haproxy 연동 지원 스크립트
## 배경: kt cloud lb(l4)는 autoscling 동작과 연계하여, 증설되는 서버가 자동으로 lb에 연결. 하지만 haproxy등의 sw lb는증설이후 후속 작업이 필요
## 기능: haproxy(mode tcp)에 autoscaling group으로 생성되는 was 서버를 연결(balance: roundrobin)
## 구현 방안: autoscaling api(listAutoScalingGroups), server api(listVirtualMachines) 호출하여"InService 상태"인 was 서버들에 대한 사설ip 목록 획득 -> 해당 사설 ip로 haproxy.conf 파일 업데이트
## crontab으로 주기적 실행

import sys,os,datetime,filecmp
from shutil import copyfile
from shutil import move


if __name__=="__main__":
	sys.path.append("/root/ktcloud-toolkit/")
	os.environ['KTCAPI'] = "APIKEY"
	os.environ['KTCSEC'] = "SECRET KEY"	

	import server
	import autoscaling as auto

	as_group_name = "AutoScaling Group Name"
	dir_conf = "haproxy config directory"	
	dir_backup = "haproxy config backup directory"
	server_count = 1

	dt = datetime.datetime.now().strftime("%Y-%m-%d-%H%M%S")
	filename = dir_backup + 'haproxy.cfg-' + dt
	
        try:
		copyfile(dir_backup+'haproxy.cfg.tmp',filename)
	except:
		print("error - copyfile:tmp")
	
	f = open(filename,'a')

	response_auto = auto.listAutoScalingGroups(zone='KR-M2',as_group_member=[as_group_name])
	vmid_list = []
	
	instance_list = response_auto['listautoscalinggroupsresponse']['autoscalinggroups'][0]['instances']
	for item in instance_list:
		if item['lifecyclestate'] == 'InService':
			vmid_list.append(item['instanceid'])
	
	vm_ip_list = []
	for vm_id in vmid_list:
		response_vm = server.listVirtualMachines(zone="KR-M2",id=vm_id)
		vm_private_ip = response_vm['listvirtualmachinesresponse']['virtualmachine'][0]['nic'][0]['ipaddress']
		vm_ip_list.append(vm_private_ip)

	for vm_ip in vm_ip_list:
		f.write("server was" + str(server_count) + " " + vm_ip  + ":5000 check fall 4 rise 2\n")
		server_count+=1
	f.close()

	diff = filecmp.cmp(dir_conf+'haproxy.cfg',filename)
        # haproxy.conf에 변화가 없으면(diff=True) 작업한 temp 파일 삭제	
        # 변화가 있을 경우, 기존 conf 파일 백업 후 신규 작업 파일로 대체/haproxy 재시작
	if diff:
		os.remove(filename)
	else:
		dt_backup = datetime.datetime.now().strftime("%Y-%m-%d-%H%M%S")
		try:
			move(dir_conf+'haproxy.cfg',dir_backup+"backup-haproxy.cfg-"+dt_backup)
			move(filename,dir_conf+'haproxy.cfg')
			os.system("/usr/sbin/service haproxy restart")
		except:
			print("file move error - haproxy.cfg")
