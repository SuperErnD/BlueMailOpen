
from pydantic import BaseModel
import settings
from fastapi import FastAPI, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import hashlib
import pyotp
class twofa(BaseModel):
    status=False
api = FastAPI()

api.mount("/static", StaticFiles(directory="static"), name="static")


templates = Jinja2Templates(directory="templates")
from pymongo import MongoClient
db = MongoClient(settings.MONGOURL)
class registrationorloginModel(BaseModel):
    email: str=None
    password: str=None
class sendModel(BaseModel):
    to: str=None
    heading: str=None
    content: str=None
messages = db['mail']['messages']
client = db['mail']['clients']
print(client)
@api.put("/api/register")
async def registration(data:registrationorloginModel):
    
    print(data)
    if not data.email:
        return {'code':400, "message":"Email is required"}
    elif not data.password:
        return {'code':400, "message":"Password is required"}
    else:
        data.email += '@bluemail.org'
        
        if client.find_one({"email": data.email}):
            return {"message":"User is already !"}
        data.password = hashlib.sha256(data.password.encode()).hexdigest()
        result = client.insert_one({"email":data.email, "password":data.password, "2fa":{"status":False}})
        return {"code":200, "message":"Successfully"}
@api.put('/api/2fa')
async def twofa(data:twofa):
    
    
    clients = client.find_one({"email": email})
    del clients['_id']
    twofa = clients['2fa']
    if bool(data.status) == True:
        if twofa['status'] == False:
            hex = pyotp.random_hex()
            base32 = pyotp.random_base32()
            status = True
            client.update_one({'email':email}, {"$set": {'2fa':{'status':status, 'hex':hex, 'base32':base32}}}, upsert=False)
            return {'message':'2FA Enabled'}
        else:
            return {'message':'Two Factor Authefication Enabled or error'}
    elif bool(data.status) == False:
        if twofa['status'] == True:
            client.update_one({'email':email}, {"$set":{'2fa':{'status':False, 'hex':None, 'base32':None}}})
            return {'message':'Disabled'}
        else:
            return {'message':'2fa no enabled...'}
    else:
        return {'message':'Bad Request', 'code':400}, 400
    
        
@api.put('/api/login')
async def login(data:registrationorloginModel):
    
    print(data)
    if not data.email:
        return {'code':400, "message":"Email is required"}
    elif not data.password:
        return {'code':400, "message":"Password is required"}
    else:
        if not data.email.endswith("@bluemail.org"):
            data.email += '@bluemail.org'
        else:
            pass
        data.password = hashlib.sha256(data.password.encode()).hexdigest()
        if client.find_one({"email":data.email, "password":data.password}):
            
            datas = client.find_one({"email":data.email, "password":data.password})
            if datas['2fa']['status'] == True:
                print(data)
                return {'code':300,'message':'Hello account is enabled 2FA verification', 'email': data.email, 'URL':f'/api/2fa/check?email={data.email}&code=None'}
                
            else:
                global email
                email = data.email
                return {"code":200, 'message':f'Welcome {data.email}'}
            
        else:
            return {'code':400, 'message':'User not found'}
@api.get('/api/2fa/generate', response_class=HTMLResponse)
async def generateqr2fa():
    email = 'diman@bluemail.org'
    if not email:
        return {'message':'Error Bad Request'}
    else:
        data = client.find_one({"email":email})
        base32 = data['2fa']['base32']
        uri = pyotp.totp.TOTP(base32).provisioning_uri(name=email, issuer_name='Blue Mail')
        return RedirectResponse(f"https://chart.googleapis.com/chart?cht=qr&chl={uri}&chs=180x180&choe=UTF-8&chld=L|2")
@api.put('/api/2fa/check')
async def checktwofa(email:str, password:str,code:int):
    
    
    if not email.endswith('@bluemail.org'):
        email += '@bluemail.org'
    password = hashlib.sha256(password.encode()).hexdigest()
    data = client.find_one({'email': email, "password":password})
    
    del password
    if not data:
        return {'message':'Error', 'code':400}
    else:
        base32 = data['2fa']['base32']
        otp = pyotp.TOTP(base32)#.provisioning_uri(name=email, issuer_name='Blue Mail') 
        print(otp.now())
        if code == int(otp.now()):
            email = email
            return {'code':200,'message':f'Welcome {email}'}
        else:
            return {'message':'Invalid key'}
          

@api.put("/api/send")
async def send(data:sendModel):
    print(data)
    
    if not data.to:
        return {'message':'Required to!'}
    elif not data.heading:
        return {'message':'Required heading!'}
    elif not data.content:
        return {'message':'Required content!'}
    else:
        if not data.to.endswith('@bluemail.org'):
            data.to += '@bluemail.org'
        if client.find_one({"email": data.to}):
            
            result = messages.insert_one({"from":email, "to":data.to, "content":data.content,"heading":data.heading})
            return {'message':'Success!'}
        else:
            result = messages.insert_one({"from":'daemonmail@bluemail.org', "to":email, "content":f"Email {data.to} not found","heading":f'Email {data.to} not found'})
            return {'message':'Success!'}
        print(result)
@api.get('/api/list')
async def list():
    try:
        tomessages = []
        frommessages = []
        for tom in messages.find({"to":email}):
            del tom['_id']
            tomessages.append(tom)
        for fromm in messages.find({"from":email}):
            del fromm['_id']
            frommessages.append(fromm)
        #tomessages = messages.find({"to":email})
        #frommessages = messages.find_one({"from":email})
    except:
        return {'code':403,'message':'you`re no logined'}
    print(tomessages)
    print(frommessages)
    try:
        del tomessages['_id']
    except:
        pass
    try:
        del frommessages['_id']
    except:
        pass
    print(tomessages)
    return {'tomessages':tomessages, "frommessages":frommessages}
@api.get("/")
async def index():
    return {'message':'API, DO NOT USE!'}

@api.get('/api')
async def ad():
    return {'message':'API, to start using api /api/login and put data email - your email, password - your password  to login read more in Read the docs'}