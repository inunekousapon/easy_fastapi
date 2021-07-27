# FastAPIの認証付き開発環境を整える

## 必要なもの

- Docker Desktop

## 作るもの

- JWTによる認証付きAPIサーバー
- ローカルのMySQLと連携

## やらないこと

- Dockerのセットアップ

## FastAPIのDockerを作る

Github公式  
https://github.com/tiangolo/uvicorn-gunicorn-fastapi-docker

```Dockerfile
FROM tiangolo/uvicorn-gunicorn-fastapi:python3.8

COPY ./app /app

RUN pip install -r requirements.txt
```

ライブラリをインストールするためにappディレクトリを作成し、requirements.txtを追加します。

```
.
├── Dockerfile
├── app
│   └── requirements.txt
```

requirements.txtにはJWTの認証に必要なライブラリとデータベースの接続に必要なものを指定しておきます。

```requirements.txt
python-jose[cryptography]== 3.3.0
passlib[bcrypt]==1.7.4
SQLAlchemy==1.4.22
pymysql==1.0.2
python-multipart==0.0.5
```

## MySQLを環境に加える

docker-compose.ymlを加えていきます。
MySQLの設定は下記のサイトを参考にしています。  
https://qiita.com/ucan-lab/items/b094dbfc12ac1cbee8cb

```docker-compose.yml
version: "3"
services:
  db:
    image: mysql:8.0
    volumes:
      - db-store:/var/lib/mysql
      - ./logs:/var/log/mysql
      - ./docker/mysql/my.cnf:/etc/mysql/conf.d/my.cnf
    environment:
      - MYSQL_DATABASE=${DB_NAME}
      - MYSQL_USER=${DB_USER}
      - MYSQL_PASSWORD=${DB_PASS}
      - MYSQL_ROOT_PASSWORD=${DB_PASS}
      - TZ=${TZ}
    ports:
      - ${DB_PORT}:3306
  web:
    build: .
    ports:
      - 80:80
    command: /start-reload.sh
    volumes:
      - ./app:/app
    environment:
      - DB_NAME=${DB_NAME}
      - DB_USER=${DB_USER}
      - DB_PASS=${DB_PASS}
      - DB_PORT=${DB_PORT}
      - DB_HOSTNAME=db
volumes:
  db-store:
```

```docker/mysql/my.cnf
# MySQLサーバーへの設定
[mysqld]
# 文字コード/照合順序の設定
character-set-server = utf8mb4
collation-server = utf8mb4_bin

# タイムゾーンの設定
default-time-zone = SYSTEM
log_timestamps = SYSTEM

# デフォルト認証プラグインの設定
default-authentication-plugin = mysql_native_password

# エラーログの設定
log-error = /var/log/mysql/mysql-error.log

# スロークエリログの設定
slow_query_log = 1
slow_query_log_file = /var/log/mysql/mysql-slow.log
long_query_time = 5.0
log_queries_not_using_indexes = 0

# 実行ログの設定
general_log = 1
general_log_file = /var/log/mysql/mysql-query.log

# mysqlオプションの設定
[mysql]
# 文字コードの設定
default-character-set = utf8mb4

# mysqlクライアントツールの設定
[client]
# 文字コードの設定
default-character-set = utf8mb4
```

```.env
DB_NAME=homestead
DB_USER=homestead
DB_PASS=secret
DB_PORT=3306
TZ=Asia/Tokyo
```

ディレクトリ構成はこうなったはずです。

```
.
├── Dockerfile
├── app
│   └── requirements.txt
├── docker
│   └── mysql
│       └── my.cnf
└── docker-compose.yml
```

## アプリケーションを書く

appフォルダ以下にmain.pyを加えていきます。

```app/main.py
from fastapi import FastAPI

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello World"}
```

ディレクトリ構成です。

```tree
.
├── Dockerfile
├── app
│   ├── app.py
│   └── requirements.txt
├── docker
│   └── mysql
│       └── my.cnf
└── docker-compose.yml
```

## 起動

起動していきましょう。

```
docker-compose up
```

しばらくすると下記のような表示が出るはずです。

```
web_1  | INFO:     Uvicorn running on http://0.0.0.0:80 (Press CTRL+C to quit)
web_1  | INFO:     Started reloader process [1] using watchgod
web_1  | INFO:     Started server process [8]
web_1  | INFO:     Waiting for application startup.
web_1  | INFO:     Application startup complete.
```

http://0.0.0.0:80 にアクセスすると下記のレスポンスが得られるはずです。

```
{"message":"Hello World"}
```

http://0.0.0.0:80/docs にアクセスするとSwagger的なドキュメントを見ることができます。


## データベース連携

appフォルダ以下に database.py というファイルを追加します。
MySQLと接続するために必要です。

```app/database.py
import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker


user = os.getenv("DB_USER")
password = os.getenv("DB_PASS")
dbname = os.getenv("DB_NAME")
hostname = os.getenv("DB_HOSTNAME")

SQLALCHEMY_DATABASE_URL = f"mysql+pymysql://{user}:{password}@{hostname}/{dbname}"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
```

appフォルダ以下に models.py というファイルを追加します。
テーブルの定義をします。

```app/models.py
from sqlalchemy import Boolean, Column, Integer, String
from sqlalchemy.orm import relationship

from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(120), index=True)
    full_name = Column(String(120))
    email = Column(String(200), unique=True, index=True)
    hashed_password = Column(String(60))
    disabled = Column(Boolean, default=True)
```

app/main.pyに下記を足します。  
本来ならばcreate_allは利用せずにmigrationツールを使いますので注意してください。

```
models.Base.metadata.create_all(bind=engine)
```

```app/main.py
from fastapi import FastAPI

import models
from database import engine

models.Base.metadata.create_all(bind=engine)

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello World"}
```

このままだとMySQLが起動する前にFastAPIサーバーが起動してしまうので起動を待つようにします。  
prestart.shというファイルをapp配下に置きます。

```app/prestart.sh
#! /usr/bin/env bash

# Let the DB start
sleep 10;
```

再度起動するとデータベースにテーブルが作成されます。


## OAuth2認証とJWT

下記の内容になります。  
https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/

app/main.pyに書き足していきます。

```app/main.py
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy.orm import Session

import models
from database import engine, SessionLocal


SECRET_KEY = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


class User(BaseModel):
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    disabled: Optional[bool] = None


class UserInDB(User):
    hashed_password: str


models.Base.metadata.create_all(bind=engine)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
app = FastAPI()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def get_user(db, username: str):
    return db.query(models.User).filter(models.User.username == username).first()


def authenticate_user(db, username: str, password: str):
    user = get_user(db, username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    user = get_user(db, username=token_data.username)
    if user is None:
        raise credentials_exception
    return user


@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/")
async def root(current_user: User = Depends(get_current_user)):
    return {"message": "Hello World"}
```

データベースのusersに下記のレコードを追加します。

|id|username|full_name|email|hashed_password|disabled|
|--|--------|---------|-----|---------------|--------|
|1|johndoe|John Doe|johndoe@example.com|$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW||


## 使い方

http://localhost:docs　に繋ぎましょう。
![image.png](https://qiita-image-store.s3.ap-northeast-1.amazonaws.com/0/105394/f67a5781-72f2-92a4-d1f0-59cb5a224ad4.png)

/ Root を開いて「Try it out」押し、Executeボタンを押すと401 Unauthorizedが返ってくるのが確認できます。
![image.png](https://qiita-image-store.s3.ap-northeast-1.amazonaws.com/0/105394/92e0635c-4f9d-a834-9e19-74d351a99f28.png)


右上のAuthorizeボタンを押すと認証フォームが表示されるので、usernameに「johndoe」、passwordに「secret」と入力して「Authorize」ボタンを押します。
![image.png](https://qiita-image-store.s3.ap-northeast-1.amazonaws.com/0/105394/12271050-8390-c7e4-1d25-de3c930a6e5a.png)

再度、/Root を開いて先程と同じ操作をすると、今度はHTTP200が返ってきます。
![image.png](https://qiita-image-store.s3.ap-northeast-1.amazonaws.com/0/105394/560485b2-753b-5d84-a260-6b28335b669b.png)


## 参考サイト

- uvicorn-gunicorn-fastapi-docker  
https://github.com/tiangolo/uvicorn-gunicorn-fastapi-docker

- MySQL8.0のコンテナ作成  
https://qiita.com/ucan-lab/items/b094dbfc12ac1cbee8cb

