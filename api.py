import os
from fastapi import FastAPI, Depends, HTTPException, Query
from dotenv import load_dotenv
from news_crawler import NewsCrawler
from news_class import News


load_dotenv()
app = FastAPI(title="NewsScraper and Groq_summary API")

def get_news_crawler() -> NewsCrawler:
    headers = {
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
      'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
      'Accept-Language': 'zh-TW,zh;q=0.8,en-US;q=0.5,en;q=0.3',
      'Referer': 'https://money.udn.com/'
    }
    return NewsCrawler(headers=headers)

@app.get("/api/scrape-news/")
async def scrape_news(category: str = Query(..., description="新聞分類"),
                    crawler: NewsCrawler = Depends(get_news_crawler)):
    """根據指定的新聞分類抓取新聞並返回結果"""

    try:
        news_category = News(source_type=category)
        crawler.generate_URLs(news_category.source_url)
        crawler.news_crawler()
        urllist = crawler.url_list
        titlelist = crawler.title_list
        contents = crawler.content_list

        picked_news = {
            "url": urllist,
            "title": titlelist,
            "content": contents,
        }
        return {"status": "success", "data": picked_news}
    except Exception as e:

        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/scrape-all-news/")
async def scrape_all_news(crawler: NewsCrawler = Depends(get_news_crawler)):
    category_list = ["要聞", "產業", "證券", "國際", "金融", "期貨", "理財", "房市", "專欄", "專題", "商情", "兩岸"]
    all_news_list = []
    
    try:
        for category in category_list:
            news_category = News(source_type=category)
            crawler.generate_URLs(news_category.source_url)
            crawler.news_crawler()

            urllist = crawler.url_list
            titlelist = crawler.title_list
            contents = crawler.content_list

            picked_news = {
                    "category": category,
                    "url": urllist,
                    "title": titlelist,
                    "content": contents
            }
            all_news_list.append(picked_news)
        return {"status": "success", "data": all_news_list}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in category {category}: {str(e)}")


@app.get("/")
def read_root():
    return {"status": "OK"}

