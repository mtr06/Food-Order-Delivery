from fastapi import FastAPI, Depends, HTTPException, status, Security, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm, HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from passlib.context import CryptContext
from datetime import datetime, timedelta
from sqlalchemy import create_engine, Column, Integer, String, JSON, DateTime, Boolean, ForeignKey, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from pydantic import BaseModel, EmailStr
from dotenv import load_dotenv
from fastapi import FastAPI, APIRouter, HTTPException, Depends, status
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Annotated, Literal, List, Optional
from datetime import datetime
from pydantic import EmailStr
import uvicorn
import jwt
import json
from dotenv import load_dotenv, dotenv_values
import mysql.connector

class Login(BaseModel):
    username: str
    password: str

class User(BaseModel):
    idUser: int
    username: str
    nomorHp: str
    isAdmin: bool
    email: str
    token: Optional[str] = None
    alamat: str

class Register(BaseModel):
    username: str
    password: str
    nomorHp: str
    email: str

# Model Pydantic untuk mendapatkan token
class Token(BaseModel):
    access_token: str
    token_type: str

class Produk(BaseModel):
    nama: str
    harga: int
    gambar: str

class Pesan(BaseModel):
    idProduk: int
    kuantitas: int

    def to_dict(self):
        return {
            "idProduk": self.idProduk,
            "kuantitas": self.kuantitas,
        }

class CreatePesanan(BaseModel):
    detail: List[Pesan]

class CreateTransaksi(BaseModel):
    metode: str
    totalHarga: int
    buktiPembayaran: str #URL

class CreatePegiriman(BaseModel):
    namaKurir: str
    nomorHp: str
    estimasi: str

app = FastAPI()

# Database Connection
cnx = mysql.connector.connect(user="admin18221064", password="foodorderdelivery098!", host="foodorder-server.mysql.database.azure.com", port=3306, database="ordev", ssl_disabled=False)


# Konfigurasi OAuth2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Konfigurasi security
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = "d23444d634fa35cd0e708c59f8d623f46e623ad82cd9f85ed438298b9dda17c9"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Dependency untuk mendapatkan pengguna berdasarkan token
def get_user(token: str = Depends(oauth2_scheme)):
    try:
        with cnx.cursor() as cursor:
            cursor.execute(f"SELECT * FROM user WHERE token = '{token}' LIMIT 1")
            user = cursor.fetchone()
            if user:
                return user
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
    finally:
        print("Getting User!")

# Fungsi untuk memverifikasi kata sandi yang sudah di-hash
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

# Fungsi untuk membuat token
def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Endpoint untuk mendapatkan token
@app.post("/token", response_model=Token, tags=["Auth"])
def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    try:
        with cnx.cursor() as cursor:
            cursor.execute(f"SELECT * FROM user WHERE username = '{form_data.username}'")
            user = cursor.fetchone()
            if user and verify_password(form_data.password, user[2]):
                # Generate token dan simpan ke database
                token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
                token = create_access_token(
                    data={"sub": user[1]}, expires_delta=token_expires
                )
                cursor.execute(f"UPDATE user SET token = '{token}' WHERE username = '{user[1]}'")
                cnx.commit()
                return {"access_token": token, "token_type": "bearer"}
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
    finally:
        print("Horeee Berhasill!!")

# Endpoint untuk mendapatkan informasi pengguna yang sudah login
@app.get("/users/me", response_model=User, tags=["Auth"])
async def read_users_me(current_user: User = Depends(get_user)):
    user_dict = {
        "idUser": current_user[0],
        "username": current_user[1],
        "nomorHp": current_user[3],
        "isAdmin": current_user[4],
        "email": current_user[5],
        "token": current_user[6],
        "alamat": current_user[7]
    }
    return user_dict

@app.post("/register", response_model=User, tags=["Register"])
async def register_user(registration_data: Register):
    try:
        with cnx.cursor() as cursor:
            cursor.execute(f"SELECT * FROM user WHERE username = '{registration_data.username}'",)
            existing_username = cursor.fetchone()
            cursor.execute(f"SELECT * FROM user WHERE email = '{registration_data.email}'")
            existing_email = cursor.fetchone()

            if(existing_username is not None or existing_email is not None):
                details = ""
                if(existing_username is not None):
                    details += "Username"
                    if(existing_email is not None):
                        details += " dan Email telah digunakan!"
                    else:
                        details += " telah digunakan!"
                else:
                    details += "Email telah digunakan!"
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail = details
                )
            
            hashed_password = pwd_context.hash(registration_data.password)
            cursor.execute("SELECT * FROM user ORDER BY idUser DESC")
            result = cursor.fetchall()
            idUser = 1
            if result is not None:
                idUser = int((result[0])[0]) + 1
            new_user = {
                "idUser": idUser,
                "username": registration_data.username,
                "password": hashed_password,
                "nomorHp": registration_data.nomorHp,
                "isAdmin": 0,
                "email": registration_data.email,
                "token" : ""
            }
            cursor.execute(f"""INSERT INTO user (idUser, username, password, nomorHp, isAdmin, email, token) 
                        VALUES ({idUser}, '{registration_data.username}', '{hashed_password}', '{registration_data.nomorHp}', 0, '{registration_data.email}', '')""")
            cnx.commit()
            return new_user
    finally:
        print("done")

@app.get("/", tags=["Root"])
def root():
    return {"message": f"Welcome to Food Order Delivery! (Created by: MTR)"}

# Route Produk
@app.get("/produk", tags=["All Can Access"])
async def get_produk():
    cursor = cnx.cursor()
    cursor.execute("Select * from produk")
    row = cursor.fetchall()

    produks = []
    
    for produk in row:
        produk_dict = {
            "idProduk": produk[0],
            "nama": produk[1],
            "harga": produk[2],
            "gambar": produk[3]
        }
        produks.append(produk_dict)

    return produks

@app.delete("/produk/{idProduk}", tags=["Admin"])
async def delete_produk(idProduk: int, current_user: User = Depends(get_user)):
    if(not current_user[4]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Method ini hanya bisa digunakan oleh Admin!"
        )
    cursor = cnx.cursor()
    cursor.execute(f"SELECT * FROM produk WHERE idProduk = {idProduk}")
    row = cursor.fetchone()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Produk with idProduk {idProduk} not found!"
        )
    cursor.execute(f"DELETE FROM produk WHERE idProduk = {idProduk}")
    cnx.commit()
    return {"message": "Produk deleted successfully"}

@app.post("/produk", tags=["Admin"])
async def add_produk(produk: Produk, current_user: User = Depends(get_user)):
    if(not current_user[4]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Method ini hanya bisa digunakan oleh Admin!"
        )
    try:
        with cnx.cursor() as cursor:
            cursor.execute("SELECT * FROM produk ORDER BY idProduk DESC")
            row = cursor.fetchall()
            idProduk = 1
            if (row is not None):
                idProduk = int((row[0])[0] + 1)
            cursor.execute(f"""SELECT * FROM produk WHERE nama = '{produk.nama}'""")
            result = cursor.fetchone()
            if (result is not None):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Produk with nama {produk.nama} sudah ada!"
                )
            else: 
                cursor.execute(f"""INSERT INTO produk (idProduk, nama, harga, gambar) 
                        VALUES ({idProduk}, '{produk.nama}', {produk.harga}, '{produk.gambar}')""")
                cnx.commit()
                return {"message": "Produk added successfully"}
              
    finally:
        print("Produk berhasil ditambahkan!")
    

@app.put("/produk/{idProduk}", tags=["Admin"])
async def update_produk(idProduk: int, produk: Produk, current_user: User = Depends(get_user)):
    if(not current_user[4]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Method ini hanya bisa digunakan oleh Admin!"
        )
    cursor = cnx.cursor()
    cursor.execute(f"SELECT * FROM produk WHERE idProduk = {idProduk}")
    row = cursor.fetchone()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Produk with idProduk {idProduk} not found!"
        )
    else:
        cursor.execute(f"""UPDATE produk SET nama = '{produk.nama}', harga = {produk.harga}, 
                 gambar = '{produk.gambar}'
                 WHERE idProduk = {idProduk}""")
        cnx.commit()

    return {"message": "Produk update successfully"}

# Route Pesan
@app.get("/pesan", tags=["Admin & Customer"])
async def get_pesanan(current_user: User = Depends(get_user)):
    try:
        with cnx.cursor() as cursor:
            pesanan = []
            if(not current_user[4]):
                cursor.execute(f"SELECT * FROM pesanan WHERE idUser = {current_user[0]}")
                result = cursor.fetchall()
                for item in result:
                    pesan_dict = {
                        "idPesanan":item[0],
                        "detail":item[2],
                        "jumlah":item[3],
                        "harga":item[4],
                        "status":item[5]
                    }
                    pesanan.append(pesan_dict)  
            else:
                cursor.execute(f"SELECT * FROM pesanan")
                result = cursor.fetchall()
                for item in result:
                    pesan_dict = {
                        "idPesanan":item[0],
                        "idUser":item[1],
                        "detail":item[2],
                        "jumlah":item[3],
                        "harga":item[4],
                        "status":item[5]
                    }
                    pesanan.append(pesan_dict)
            return pesanan
    finally:
        print("Read Pesanan")

@app.post("/pesan", tags=["Customer"])
async def add_pesanan(list_pesanan: CreatePesanan, current_user: User = Depends(get_user)):
    if(current_user[4]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Method ini hanya bisa digunakan oleh Customer!"
        )
    try:
        with cnx.cursor() as cursor:
            cursor.execute("SELECT * FROM produk")
            produk_dict = {produk[0]: {"harga": produk[2]} for produk in cursor.fetchall()}

            total_harga = 0
            jumlah = 0
            pesanan_details = [pesan.to_dict() for pesan in list_pesanan.detail]

            for pesan in list_pesanan.detail:
                id_produk = pesan.idProduk
                kuantitas = pesan.kuantitas
                if id_produk not in produk_dict:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Produk with idProduk {id_produk} not found!"
                    )
                harga_produk = produk_dict[id_produk]["harga"]
                jumlah += kuantitas
                total_harga += harga_produk * kuantitas
            cnx.commit()
            cursor.execute("SELECT * FROM pesanan ORDER BY idPesanan DESC")
            rp = cursor.fetchone()
            idPesanan = 1
            if(rp is not None):
                idPesanan = int(rp[0]) + 1
            cursor.execute(
                f"""INSERT INTO pesanan (idPesanan, idUser, detail, jumlah, harga, status)
                    VALUES ({idPesanan}, {current_user[0]}, '{json.dumps(pesanan_details)}', {jumlah}, {total_harga}, 0)""",
            )
            # Lanjutkan!!
            cnx.commit()
            return {"message" : "Berhasil menambahkan pesanan!"}
    finally:
        print("Add Pesanan")

@app.put("/pesan/{idPesanan}", tags=["Customer"])
async def do_pembayaran(idPesanan: int, data_transaksi: CreateTransaksi, current_user: User = Depends(get_user)):
    if(current_user[4]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Method ini hanya bisa digunakan oleh Customer!"
        )
    try:
        with cnx.cursor() as cursor:
            cursor.execute(f"SELECT * FROM pesanan WHERE idPesanan = {idPesanan}")
            pesanan = cursor.fetchone()
            if(pesanan is None):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Pesanan dengan idPesanan {idPesanan} tidak ditemukan!"
                )
            if(pesanan[1] != current_user[0]):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Pesanan dengan idPesanan {idPesanan} bukanlah pesananmu!"
                )
            cursor.execute(f"SELECT * FROM transaksi WHERE idPesanan = {idPesanan}")
            transaksi = cursor.fetchone()
            tanggal = datetime.utcnow()
            sisa = 0
            if(transaksi is None):
                cursor.execute(f"SELECT * FROM transaksi ORDER BY idTransaksi DESC")
                lt = cursor.fetchone()
                idTransaksi = 1
                if(lt is not None):
                    idTransaksi += lt[0]
                sisa = pesanan[4] - data_transaksi.totalHarga
                bayar = 0
                if(sisa < 0):
                    bayar = pesanan[4]
                else:
                    bayar = data_transaksi.totalHarga
                if sisa <= 0:
                    cursor.execute(
                        f"""UPDATE pesanan SET status = 1
                        WHERE idPesanan = {idPesanan}""",
                    )
                cursor.execute(
                    f"""INSERT INTO transaksi (idTransaksi, idPesanan, idUser, metode, tanggal, totalHarga, verifikasi, buktiPembayaran)
                        VALUES ({idTransaksi}, {idPesanan}, {current_user[0]}, '{data_transaksi.metode}', '{tanggal}', {bayar}, 0, '{data_transaksi.buktiPembayaran}')""",
                )
            else:
                sisa = pesanan[4] - transaksi[5] - data_transaksi.totalHarga
                if(sisa < 0):
                    bayar = pesanan[4]
                else:
                    bayar = transaksi[5] + data_transaksi.totalHarga
                if sisa <= 0:
                    cursor.execute(
                        f"""UPDATE pesanan SET status = 1
                        WHERE idPesanan = {idPesanan}""",
                    )
                cursor.execute(
                    f"""UPDATE transaksi SET metode = '{data_transaksi.metode}', totalHarga = {bayar}, buktiPembayaran = '{data_transaksi.buktiPembayaran}'
                    WHERE idPesanan = {idPesanan}""",
                )
            cnx.commit()
            if(sisa > 0):
                return {"message" : f"Total yang harus dibayar adalah sebesar Rp {sisa}"}
            elif(sisa == 0):
                return {"message" : f"Pembayaran telah selesai!"}
            else:
                return {"message" : f"Pembayaran telah selesai! Uang kembalian anda sebesar Rp {-1*sisa}"}

    finally:
        print("Do Pembayaran")

# Route Transaksi
@app.get("/transaksi", tags=["Admin"])
async def get_transaksi(current_user: User = Depends(get_user)):
    if(not current_user[4]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Method ini hanya bisa digunakan oleh Admin!"
        )
    try:
        with cnx.cursor() as cursor:
            cursor.execute("Select * from Transaksi")
            row = cursor.fetchall()

            transaksi = []
            
            for item in row:
                transaksi_dict = {
                    "idTransaksi": item[0],
                    "idPesanan": item[1],
                    "idUser": item[2],
                    "metode": item[3],
                    "tanggal": item[4],
                    "totalHarga": item[5],
                    "verifikasi": item[6],
                    "buktiPembayara": item[7],
                }
                transaksi.append(transaksi_dict)

            return transaksi
    finally:
        print("Get Transaksi")

# Route Transaksi
@app.put("/transaksi/{idTransaksi}", tags=["Admin"])
async def verifikasi_transaksi(idTransaksi: int, pengiriman: CreatePegiriman, current_user: User = Depends(get_user)):
    if(not current_user[4]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Method ini hanya bisa digunakan oleh Admin!"
        )
    try:
        with cnx.cursor() as cursor:
            cursor.execute(f"Select * from transaksi WHERE idTransaksi = {idTransaksi}")
            transaksi = cursor.fetchone()
            if(transaksi is None):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Trannsaksi dengan idTransaksi {idTransaksi} tidak ditemukan!"
                )
            cursor.execute(f"Select * from pesanan WHERE idPesanan = {transaksi[1]}")
            pesanan = cursor.fetchone()
            if(transaksi is None):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Pesanan dengan idPesanan {transaksi[1]} tidak ditemukan!"
                )
            if(not pesanan[5]):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Pesanan dengan idPesanan {transaksi[1]} masih belum menyelesaikan pembayaran!"
                )
            cursor.execute("SELECT * FROM pengiriman ORDER BY idPengiriman DESC")
            pr = cursor.fetchone()
            idPengiriman = 1
            if(pr is not None):
                idPengiriman += int(pr[0])
            
            cursor.execute(f"""INSERT INTO pengiriman (idPengiriman, idTransaksi, namaKurir, nomorHp, estimasi, status, alamatTujuan)
                        VALUES ({idPengiriman}, {idTransaksi}, '{pengiriman.namaKurir}', '{pengiriman.nomorHp}', '{pengiriman.estimasi}', 0, '{current_user[7]}')""")
            cursor.execute(
                        f"""UPDATE transaksi SET verifikasi = 1
                        WHERE idTransaksi = {idTransaksi}""")
            cnx.commit()
            return {"message" : f"Transaksi dengan idTransaksi {idTransaksi} berhasil diverifikasi!"}
    finally:
        print("Get Transaksi")
    
# Route Pengiriman
@app.get("/pengiriman", tags=["Admin & Customer"])
async def get_pengiriman(current_user: User = Depends(get_user)):
    try:
        with cnx.cursor() as cursor:
            pengiriman = []
            if(not current_user[4]):
                cursor.execute(f"SELECT * FROM pengiriman INNER JOIN transaksi WHERE idUser = {current_user[0]}")
                result = cursor.fetchall()
                for item in result:
                    pengiriman_dict = {
                        "idTransaksi":item[1],
                        "namaKurir":item[2],
                        "nomorHp":item[3],
                        "estimasi":item[4],
                        "status":item[5]
                    }
                    pengiriman.append(pengiriman_dict)  
            else:
                cursor.execute(f"SELECT * FROM pengiriman")
                result = cursor.fetchall()
                for item in result:
                    pengiriman_dict = {
                        "idPengiriman":item[0],
                        "idTransaksi":item[1],
                        "namaKurir":item[2],
                        "nomorHp":item[3],
                        "estimasi":item[4],
                        "status":item[5]
                    }
                    pengiriman.append(pengiriman_dict)  
            return pengiriman
    finally:
        print("Get Pengiriman")

# Route Pengiriman
@app.put("/pengiriman/{idPengiriman}", tags=["Admin"])
async def verifikasi_pengiriman(idPengiriman: int ,current_user: User = Depends(get_user)):
    if(not current_user[4]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Method ini hanya bisa digunakan oleh Admin!"
        )
    try:
        with cnx.cursor() as cursor:
            cursor.execute(f"SELECT * FROM pengiriman WHERE idPengiriman = {idPengiriman}")
            pengiriman = cursor.fetchone()
            if(pengiriman is None):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Pengiriman dengan idPengiriman {idPengiriman} tidak ditemukan!"
                )
            cursor.execute(
                        f"""UPDATE pengiriman SET status = 1
                        WHERE idPengiriman = {idPengiriman}""")
            cnx.commit()
            return {"message" : "Verifikasi pengiriman telah sampai berhasil!"}
    finally:
        print("Verifikasi Pengiriman")
