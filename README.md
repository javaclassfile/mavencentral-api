# mavencentral-api

## Run
### Ubuntu 24.04 - NameCheap VPS


Install
```
apt install python3-pip
apt install python3-fastapi
apt install python3-venv

python3 -m venv venv
source venv/bin/activate
(venv) root@server1:~/mavencentral-api# pip install "fastapi[standard]"
(venv) root@server1:~/mavencentral-api# deactivate
```

Run
```
./venv/bin/fastapi run --port 80
```

Access Point
- [http://mavencentral.xyz/](http://mavencentral.xyz/)
- [http://mavencentral.xyz/docs](http://mavencentral.xyz/docs)



#### Run as Ubuntu service
- Reference: [Google AI Overview](https://www.google.com/search?q=ubuntu+make+fastapi+server+run+when+startup)


Create [`fastapi.service`](fastapi.service)

```
sudo nano /etc/systemd/system/fastapi.service

systemctl daemon-reload
systemctl list-unit-files

systemctl enable fastapi.service
systemctl restart fastapi
systemctl status fastapi
```


### Ubuntu 24.04 - WSL

Install
```
pip install fastapi uvicorn
pip install "fastapi[standard]"
```

Run
```
fastapi run
```
Access Point
- [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)


## Database

This site need a database file named `mavendb.sqlite`
- This file is very big (`26` GB or more) so it is not in github repo but delivered separately
