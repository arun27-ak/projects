import os,re,time,pandas as pd
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

IMDB_URL="https://www.imdb.com/chart/top/"
CURRENT_FILE="imdb_current.csv"
HISTORY_FILE="imdb_history.csv"
TARGET_MOVIES=250

def create_driver():
    options=Options()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36")
    driver=webdriver.Chrome(service=Service(ChromeDriverManager().install()),options=options)
    driver.set_page_load_timeout(60)
    return driver

def clean_text(text):
    return " ".join(str(text or "").split()).strip()

def clean_name(name):
    name=clean_text(name)
    name=re.sub(r"^View title page for\s*","",name,flags=re.I)
    name=re.sub(r"^\d+\.\s*","",name)
    return clean_text(name)

def extract_movies(driver):
    script="""
    const rows=[...document.querySelectorAll('li.ipc-metadata-list-summary-item')];
    const movies=[];
    for(let row of rows){
        if(movies.length>=250) break;
        let url="";
        for(let link of row.querySelectorAll('a[href*="/title/tt"]')){
            let m=(link.getAttribute("href")||"").match(/\\/title\\/(tt\\d+)/);
            if(m){url="https://www.imdb.com/title/"+m[1]+"/";break;}
        }
        let title="";
        let e=row.querySelector("h3.ipc-title__text");
        if(e) title=e.textContent.trim();
        if(!title){
            e=row.querySelector("a.ipc-title-link-wrapper");
            if(e) title=e.textContent.trim();
        }
        let year="";
        let metadata=[...row.querySelectorAll("[class*='cli-title-metadata-item']")];
        for(let e of metadata){
            let v=e.textContent.trim();
            if(/^(19\\d{2}|20\\d{2})$/.test(v)){year=v;break;}
        }
        if(!year){
            for(let e of row.querySelectorAll("*")){
                let v=(e.textContent||"").trim();
                if(/^(19\\d{2}|20\\d{2})$/.test(v)){year=v;break;}
            }
        }
        let rating="";
        let r=row.querySelector("span.ipc-rating-star--rating");
        if(r) rating=r.textContent.trim();
        if(!rating){
            for(let e of row.querySelectorAll("span")){
                let v=e.textContent.trim();
                if(/^\\d\\.\\d$/.test(v)){rating=v;break;}
            }
        }
        if(title&&url) movies.push({movie_name:title,year:year,imdb_rating:rating,url:url});
    }
    return movies;
    """
    return driver.execute_script(script)

def clean_movies(raw):
    movies=[]
    seen=set()
    for x in raw:
        url=clean_text(x.get("url","")).split("?")[0]
        if url and not url.endswith("/"): url+="/"
        if not url or url in seen: continue
        seen.add(url)
        name=clean_name(x.get("movie_name",""))
        year=clean_text(x.get("year",""))
        rating=clean_text(x.get("imdb_rating",""))
        if not year:
            m=re.search(r"\b(19\d{2}|20\d{2})\b",name)
            year=m.group(1) if m else ""
        m=re.search(r"\b([0-9]\.[0-9])\b",rating)
        rating=m.group(1) if m else ""
        movies.append({"rank":len(movies)+1,"movie_name":name,"year":year,"imdb_rating":rating,"url":url})
        if len(movies)>=250: break
    return movies

def validate(movies):
    fields=["movie_name","year","imdb_rating","url"]
    print("\n"+"="*60+"\nDATA VALIDATION\n"+"="*60)
    print(f"Total movies  : {len(movies)}/250")
    for field in fields:
        print(f"{field.replace('_',' ').title():15}: {sum(bool(x[field]) for x in movies)}/250")
    unique=len(set(x["url"] for x in movies))
    print(f"Unique URLs   : {unique}/250")
    return len(movies)==250 and all(all(x[f] for x in movies) for f in fields) and unique==250

def save_files(movies):
    date=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    df=pd.DataFrame(movies)
    df["scraping_date"]=date
    df.to_csv(CURRENT_FILE,index=False,encoding="utf-8-sig")
    if os.path.exists(HISTORY_FILE):
        try:
            old=pd.read_csv(HISTORY_FILE)
            df=pd.concat([old,df],ignore_index=True)
        except Exception:
            pass
    df.to_csv(HISTORY_FILE,index=False,encoding="utf-8-sig")
    print(f"\nSaved: {CURRENT_FILE}")
    print(f"Saved: {HISTORY_FILE}")

def main():
    start=time.time()
    driver=None
    try:
        print("="*60)
        print("IMDb TOP 250 MOVIE SCRAPER")
        print("="*60)
        driver=create_driver()
        print("Opening IMDb Top 250...")
        driver.get(IMDB_URL)
        WebDriverWait(driver,30).until(EC.presence_of_element_located((By.TAG_NAME,"body")))
        time.sleep(4)
        print("Loading movies...")
        last=0
        for _ in range(25):
            driver.execute_script("window.scrollTo(0,document.body.scrollHeight);")
            time.sleep(1)
            new=driver.execute_script("return document.body.scrollHeight;")
            if new==last: break
            last=new
        driver.execute_script("window.scrollTo(0,0);")
        rows=driver.find_elements(By.CSS_SELECTOR,"li.ipc-metadata-list-summary-item")
        print(f"Movie containers found: {len(rows)}")
        if len(rows)<250:
            print("ERROR: Less than 250 movie containers found.")
            return
        movies=clean_movies(extract_movies(driver))
        print(f"Movies extracted: {len(movies)}")
        for i,movie in enumerate(movies,1): movie["rank"]=i
        print("\n"+"="*60+"\nFIRST 10 MOVIES\n"+"="*60)
        for m in movies[:10]:
            print(f"{m['rank']}. {m['movie_name']} | {m['year']} | {m['imdb_rating']} | {m['url']}")
        if not validate(movies):
            print("\nERROR: Validation failed. CSV files were not updated.")
            return
        save_files(movies)
        print("\n"+"="*60)
        print("SCRAPING COMPLETED SUCCESSFULLY")
        print("="*60)
        print(f"Movies: {len(movies)}")
        print(f"Time: {time.time()-start:.2f} seconds")
    except Exception as e:
        print(f"\nERROR: {e}")
    finally:
        if driver: driver.quit()
        print("Chrome closed.")

if __name__=="__main__":
    main()