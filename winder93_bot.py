#!/usr/bin/env python3

import sys
import datetime
import re
import urllib.parse
import configparser
import json
import time
import requests
import random
from bs4 import BeautifulSoup
import redis

config = configparser.ConfigParser() # Настройки
config.read("settings.ini")

baseurl = config["MySpace"]["baseurl"]

# Бот
s = requests.session()
headers = {'content-type': 'application/x-www-form-urlencoded'}

def logIn(login, password):
	payload_login = "username={}&password={}&login=".format(urllib.parse.quote(login), urllib.parse.quote(password))
	s.request("POST", baseurl + "/login.php", data=payload_login, headers=headers)

def acceptFwiendRequest(fwiendId):
	s.request("GET", baseurl + "/accept.php?id={}".format(fwiendId))

def getFwiendsRequests(id):
	r = s.request("GET", baseurl + "/requests.php?id={}".format(id))
	bs = BeautifulSoup(r.text, features="html.parser")
	return [int(a.get("href")[len("index.php?id="):])
		for a in bs.select('div.friendRequests>a')]

def logOut():
	s.post(baseurl + "/logout.php")

def saveConfig():
	with open('settings.ini', 'w') as configfile:
		config.write(configfile)

def shutDown():
	saveConfig()
	logOut()
	sys.exit(0)

def getAllUsers():
	r = s.request("GET", baseurl + "/api.php")
	j = json.loads(r.text)
	if j['success'] == 'false':
		return {}
	return j['fwiends']

def getUserInfo(id):
	r = s.request("GET", baseurl + "/api.php?id={}".format(id))
	j = json.loads(r.text)
	if j['success'] == 'false':
		return {}
	return j

def updateDB():
	pass

logIn(config["MySpace"]["email"], config["MySpace"]["password"])

for fwiend in getFwiendsRequests(config["MySpace"]["id"]):
	print("New fwiend request:", fwiend)
	acceptFwiendRequest(fwiend)

# Код ниже
r = redis.Redis(host=config['Redis']['host'],
	port=int(config['Redis']['port']),
	db=int(config['Redis']['db']))

all_users = getAllUsers()
time.sleep(11) # 10 секунд между запросами + 1 секунда чтоб наверняка
fwiends = getUserInfo(config['MySpace']['id'])['fwiends'][1:] # Без Тома
users = {}
max_fwiends = 0
for user in all_users:
	u = int(user)
	if u not in [1, int(config['MySpace']['id'])] and u not in fwiends and all_users[user]['name'] != 'User Banned':
		users[user] = all_users[user]['fwiends']
		if users[user] > max_fwiends:
			max_fwiends = users[user]

fwiends_sorted_list = {}
for x in fwiends:
	fwiends_sorted_list[x] = all_users[str(x)]['fwiends']

r.zadd('priority_users', fwiends_sorted_list)
r.zadd('users', users)

pu_shuffled = r.zrangebyscore('priority_users', '-inf', '+inf')
random.shuffle(pu_shuffled)
for pu in pu_shuffled:
	r.sadd('priority_users_shuffled', pu)
u_shuffled = r.zrangebyscore('users', 2, max_fwiends // 15) # Начинаем от 2х друзей, потому что это небольшая гарантия того, что пользователь не просто зарегистрировался и вышел
random.shuffle(u_shuffled)
for u in u_shuffled:
	r.sadd('users_shuffled', u)

shutDown()
