(()=>{
"use strict";
const $ = id => document.getElementById(id);
const map = L.map("map").setView([23.8,120.9],7);
L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",{
  attribution:'© <a href="https://www.openstreetmap.org/copyright" target="_blank">OpenStreetMap contributors</a>',
  maxZoom:19
}).addTo(map);
const cluster = L.markerClusterGroup({maxClusterRadius:45,spiderfyOnMaxZoom:true});
map.addLayer(cluster);
let all=[], activeMode="safe";
const text=(tag,content,cls)=>{
  const e=document.createElement(tag);e.textContent=content??"";
  if(cls)e.className=cls;return e;
};
const selectOptions=(id,values,first)=>{
  const el=$(id);el.replaceChildren(new Option(first,""));
  [...new Set(values.filter(Boolean))].sort().forEach(v=>el.add(new Option(v,v)));
};
const accuracyLabel=a=>({
  location:"ClickUp 精確座標",
  address:"地址定位",
  street:"街道定位（非門牌）",
  city:"縣市概略定位",
  approximate:"概略定位"
})[a]||"未確認定位精度";
const fit=()=>{
  if(cluster.getLayers().length)map.fitBounds(cluster.getBounds().pad(0.15),{maxZoom:12});
  else map.setView([23.8,120.9],7);
};
function render(){
  cluster.clearLayers();
  const q=$("searchInput").value.trim().toLowerCase();
  const city=$("countySelect").value,status=$("statusSelect").value;
  const shown=all.filter(c=>(!city||c.county===city)&&(!status||c.status===status)
    &&(!q||[c.name,c.county,c.address,c.status].join(" ").toLowerCase().includes(q)));
  $("visibleCount").textContent=shown.length;
  const list=document.createDocumentFragment();
  for(const c of shown){
    const accurate=["location","address","street"].includes(c.accuracy);
    const pin=L.divIcon({className:"map-pin-wrapper",
      html:'<span class="customer-pin '+(accurate?"precise-pin":"approx-pin")+'"></span>',
      iconSize:[20,20],iconAnchor:[10,10]});
    const marker=L.marker([c.lat,c.lng],{icon:pin});
    const popup=text("div",c.name,"customer-name");
    popup.append(text("div",c.address||c.county||"","customer-address"));
    popup.append(text("div",accuracyLabel(c.accuracy),"customer-foot"));
    if(c.status)popup.append(text("div","狀態："+c.status,"customer-foot"));
    if(c.url&&/^https:\/\/app\.clickup\.com\/t\//.test(c.url)){
      const a=text("a","開啟 ClickUp 客戶資料 ↗");
      a.href=c.url;a.target="_blank";a.rel="noopener noreferrer";
      popup.append(a);
    }
    if(activeMode==="private" && c.address){
      const mapsLink=text("a","以地址開啟 Google Maps ↗");
      mapsLink.href="https://www.google.com/maps/search/?api=1&query="+encodeURIComponent(c.address);
      mapsLink.target="_blank";mapsLink.rel="noopener noreferrer";
      popup.append(text("div","","customer-foot"),mapsLink);
    }
    marker.bindPopup(popup);
    cluster.addLayer(marker);
    const b=text("button","","customer");b.type="button";
    b.append(text("div",c.name,"customer-name"));
    b.append(text("div",c.address||c.county||"","customer-address"));
    b.append(text("div",accuracyLabel(c.accuracy),"customer-foot"));
    b.addEventListener("click",()=>cluster.zoomToShowLayer(marker,()=>{
      map.setView(marker.getLatLng(),accurate?16:10);
      marker.openPopup();
    }));
    list.append(b);
  }
  $("customerList").replaceChildren(list);
  if(!shown.length)$("customerList").append(text("div",
    "目前沒有符合條件且可定位的客戶資料。","empty-state"));
  fit();
}
function setData(data,secure){
  activeMode=secure?"private":"safe";
  all=(data.customers||[]).filter(c=>Number.isFinite(c.lat)&&Number.isFinite(c.lng));
  $("metricTasks").textContent=data.total_tasks??0;
  $("metricLocated").textContent=all.length;
  $("metricCounties").textContent=new Set(all.map(c=>c.county).filter(Boolean)).size;
  $("metricMissing").textContent=(data.missing_location||0)+(data.without_address||0);
  $("syncTime").textContent=data.generated_at||"尚未同步";
  $("privacyBanner").textContent=secure
    ?"已解鎖：完整客戶名稱與地址僅在這個瀏覽器中解密，關閉頁面即需重新解鎖"
    :"公開展示：匿名客戶及概略位置（未解鎖）";
  $("searchInput").value="";
  selectOptions("countySelect",all.map(c=>c.county),"所有縣市");
  selectOptions("statusSelect",all.map(c=>c.status),"所有狀態");
  render();
  const legend=document.querySelector(".bottom-right");
  if(legend)legend.textContent=secure
    ? "綠色：地址／座標定位；橘色：縣市概略位置。定位精度依來源而異"
    : "目前為匿名概略位置；解鎖後才能查看客戶名稱與地址";
}
const fromBase64=s=>Uint8Array.from(atob(s),ch=>ch.charCodeAt(0));
async function decryptPayload(doc,password){
  const bytes=new TextEncoder().encode(password);
  const k=await crypto.subtle.importKey("raw",bytes,"PBKDF2",false,["deriveKey"]);
  const aes=await crypto.subtle.deriveKey({
    name:"PBKDF2",hash:"SHA-256",iterations:doc.iterations,
    salt:fromBase64(doc.salt)
  },k,{name:"AES-GCM",length:256},false,["decrypt"]);
  const decoded=await crypto.subtle.decrypt(
    {name:"AES-GCM",iv:fromBase64(doc.iv)},
    aes,fromBase64(doc.ciphertext)
  );
  return JSON.parse(new TextDecoder().decode(decoded));
}
function unlockView(){
  const panel=$("privacyBanner").parentElement;
  const wrapper=text("section","","unlock-card");
  wrapper.id="secureUnlock";
  const heading=text("strong","查看真實客戶地圖");
  const blurb=text("p","輸入地圖解鎖密碼後，顯示公司名稱、完整地址、ClickUp 連結及定位精度。");
  const row=text("div","","unlock-row");
  const input=document.createElement("input");input.type="password";
  input.placeholder="地圖解鎖密碼";input.autocomplete="off";input.id="mapPassword";
  const button=text("button","解鎖","unlock-button");button.type="button";
  const msg=text("p","正在檢查加密資料…","unlock-message");msg.setAttribute("role","status");
  row.append(input,button);
  wrapper.append(heading,blurb,row,msg);
  panel.insertBefore(wrapper,$("privacyBanner"));
  let secureDoc=null;
  fetch("./customers.secure.json",{cache:"no-store"}).then(r=>{
    if(!r.ok)throw new Error("尚未產生加密資料");
    return r.json();
  }).then(doc=>{
    if(!doc.ciphertext||!doc.iv||!doc.salt)throw new Error("加密資料不完整");
    secureDoc=doc;msg.textContent="可解鎖完整客戶地圖。";
  }).catch(()=>{
    msg.textContent="尚未啟用完整資料。請設定 MAP_PASSPHRASE 並重新執行 GitHub Actions。";
    button.disabled=true;
  });
  async function unlock(){
    if(!secureDoc)return;
    if(!input.value){msg.textContent="請先輸入密碼";return;}
    button.disabled=true;button.textContent="解密中…";
    try{
      const data=await decryptPayload(secureDoc,input.value);
      if(!Array.isArray(data.customers))throw Error("格式錯誤");
      setData(data,true);
      input.value="";wrapper.replaceChildren(
        text("strong","已解鎖完整客戶地圖"),
        text("p","目前顯示真實客戶名稱及地址，請勿將畫面分享給未授權人員。")
      );
    }catch(e){
      msg.textContent="解鎖失敗：請確認密碼與 MAP_PASSPHRASE 完全相同。";
      input.value="";
    }finally{button.disabled=false;button.textContent="解鎖";}
  }
  button.addEventListener("click",unlock);
  input.addEventListener("keydown",e=>{if(e.key==="Enter")unlock();});
}
$("fitBtn").addEventListener("click",fit);
$("resetBtn").addEventListener("click",()=>{
  $("searchInput").value="";$("countySelect").value="";$("statusSelect").value="";render();
});
for(const id of ["searchInput","countySelect","statusSelect"]){
  $(id).addEventListener(id==="searchInput"?"input":"change",render);
}
fetch("./customers.json",{cache:"no-store"}).then(r=>{
  if(!r.ok)throw Error("公開展示資料尚未產生");
  return r.json();
}).then(data=>setData(data,false)).catch(e=>{
  $("customerList").replaceChildren(text("p",e.message,"empty-state"));
  $("syncTime").textContent="尚未同步";
});
unlockView();
})();
