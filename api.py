import asyncio
import os
from fastapi import FastAPI, Depends, HTTPException, Query
from dotenv import load_dotenv
from news_crawler import NewsCrawler
from news_class import News
from anyio import to_thread

load_dotenv()
app = FastAPI(title="NewsScraper API")

# 設定信號標，限制同時只有 2 個執行緒在爬網頁
sem = asyncio.Semaphore(2)

def get_headers():
    return {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-TW,zh;q=0.8,en-US;q=0.5,en;q=0.3',
        'Referer': 'https://money.udn.com/'
    }

def scrape_task_sync(category: str):
    """
    這是在執行緒中運行的同步爬蟲邏輯。
    為了避免多執行緒衝突，我們在每個任務內建立獨立的 crawler。
    因為是同步的所以要等一個類別爬完才能換下一個類別。
    """
    crawler = NewsCrawler(headers=get_headers())
    
    news_category = News(source_type=category)
    crawler.generate_URLs(news_category.source_url)
    crawler.news_crawler()

    return {
        "category": category,
        "image": crawler.image_list,
        "url": crawler.url_list,
        "title": crawler.title_list,
        "content": crawler.content_list
    }

async def semaphore_scrape(category: str):
    """控制併發數量的包裝函式"""
    async with sem: # <--- (最多 2 個任務同時進行)
        # 將同步的爬蟲任務丟進執行緒池執行
        result = await to_thread.run_sync(scrape_task_sync, category)
        # 爬完一個類別後，休息 1 秒再釋放配額，防止過快
        await asyncio.sleep(1) 
        return result

@app.get("/api/scrape-all-news/")
async def scrape_all_news():
    category_list = ["要聞", "產業", "證券", "國際", "金融", "期貨", "理財", "房市", "專欄", "專題", "商情", "兩岸"]
    
    try:
        # 建立所有類別的任務清單
        tasks = [semaphore_scrape(cat) for cat in category_list]
        
        # 同時啟動所有任務，但會受限於 Semaphore(2)
        all_news_list = await asyncio.gather(*tasks)

        return {"status": "success", "data": all_news_list}

    except Exception as e:
        # 注意：這裡不再使用單一 category 變數，因為是併發執行
        raise HTTPException(status_code=500, detail=f"Scraping failed: {str(e)}")

@app.get("/")
def read_root():
    return {"status": "OK"}