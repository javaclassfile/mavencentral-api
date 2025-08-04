# mavencentral-api

## Run
### Ubuntu 24.04 Empty (OVH VPS)


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

###  WSL

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
