### Readme.md

Digital Humanities For CS students 2019
Adi Marantz and Embar Almog

### KIMA Reconciliation

 This is a reconciliation service that can be used in OpenRefine.
 The used API is: http://kimaorg.azurewebsites.net/swagger/index.html

### Installation Steps

- Install Python3.7
- Make sure you insert pip.exe into your system env (Found in %USERPROFILE%\AppData\Local\Programs\Python\Python37-{Release num}\Scripts\pip.exe)
- run: `pip install -r requirements.txt`

### Running The Server

- Run `server.py`
- Open your OpenRefine project
- Add new service with: `localhost:3200/api` URL
