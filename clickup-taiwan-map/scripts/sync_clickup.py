import os,json,re,datetime,shutil,pathlib,requests
ROOT=pathlib.Path(__file__).resolve().parents[1]
ID="901800292253"
ADDR="005e585c-bce2-4f59-9dcd-ff1cfbe1aa63"
LOC="0e79099e-1e0e-4a5f-a6ef-acdc4da3f1eb"
CITIES={"基隆市":(25.13,121.74),"臺北市":(25.03,121.56),"新北市":(25.01,121.46),"桃園市":(24.99,121.30),"新竹市":(24.81,120.97),"新竹縣":(24.84,121.02),"苗栗縣":(24.56,120.82),"臺中市":(24.15,120.67),"彰化縣":(24.08,120.54),"南投縣":(23.96,120.97),"雲林縣":(23.71,120.43),"嘉義市":(23.48,120.45),"嘉義縣":(23.45,120.26),"臺南市":(23.00,120.23),"高雄市":(22.63,120.30),"屏東縣":(22.55,120.55),"宜蘭縣":(24.76,121.75),"花蓮縣":(23.99,121.60),"臺東縣":(22.76,121.14),"澎湖縣":(23.57,119.58),"金門縣":(24.43,118.32),"連江縣":(26.16,119.95)}
def field(t,fid,name):
 for x in t.get("custom_fields",[]):
  if x.get("id")==fid:return x.get("value")
 for x in t.get("custom_fields",[]):
  if x.get("name")==name:return x.get("value")
 return None
def address(x):
 if isinstance(x,str):return x.strip()
 if isinstance(x,dict):
  for k in ("formatted_address","address","name"):
   if isinstance(x.get(k),str) and x[k].strip():return x[k].strip()
 return ""
def coords(x):
 if not isinstance(x,dict):return None
 v=x.get("location",x)
 if not isinstance(v,dict):return None
 try:
  lat=float(v["lat"]);lng=float(v.get("lng",v.get("lon")))
  return (lat,lng) if 21<=lat<=27 and 117<=lng<=124 else None
 except (ValueError,TypeError,KeyError):return None
def main():
 token=os.getenv("CLICKUP_TOKEN","").strip()
 if not token:raise RuntimeError("Set CLICKUP_TOKEN in repository Actions secrets")
 session=requests.Session()
 tasks=[]
 for page in range(1000):
  response=session.get(f"https://api.clickup.com/api/v2/list/{ID}/task",headers={"Authorization":token},params={"page":page,"include_closed":"true","subtasks":"false"},timeout=45)
  response.raise_for_status()
  batch=response.json()["tasks"];tasks.extend(batch)
  if len(batch)<100:break
 else:raise RuntimeError("Pagination exceeded 1000 pages")
 mode="safe"
 customers=[];without=0;unlocated=0
 for t in tasks:
  location=field(t,LOC,"公司地址")
  addr=address(field(t,ADDR,"地址")) or address(location)
  crd=coords(location)
  city=next((c for c in CITIES if c in addr.replace("台","臺")),"")
  if not city:
   city=next((c for c in CITIES if c[:2] in addr.replace("台","臺")),"")
  if not addr and not crd:without+=1;continue
  if not crd and city:crd=CITIES[city]
  if not crd:unlocated+=1;continue
  i=len(customers)+1
  customers.append({"id":f"c{i}","name":f"客戶 {i:03d}","address":city or "臺灣","status":"","url":"","county":city or "其他","lat":round(crd[0],1),"lng":round(crd[1],1),"accuracy":"approximate"})
 result={"generated_at":datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(timespec="minutes"),"mode":mode,"total_tasks":len(tasks),"located":len(customers),"missing_location":unlocated,"without_address":without,"customers":customers}
 (ROOT/"customers.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
 print(f"Located {len(customers)}/{len(tasks)} customers (safe public mode)")
if __name__=="__main__":main()
