from bs4 import BeautifulSoup
from pathlib import Path
from urllib.parse import urlparse
import json
import requests
import time
import datetime
import pytz
from zoneinfo import ZoneInfo
import re

class NewsCrawler:
  def __init__(self, headers):

    self.url = ""
    self.headers = headers
    self.url_list = []
    self.title_list = []
    self.image_list = []
    self.keywords_list = []
    self.content_list = []
    self.all_news_list = []
    self.history_url_list = set()
    self.history_title_list = set()
    self.DEFAULT_IMAGE = "https://pgw.udn.com.tw/gw/photo.php?u=https://udn.com/upf/2017_news/noimg_cid6638_5.jpg"

  def _generate_uni_news_list(self, any_list):
    uni_new_list = set()
    _list = []
    for item in any_list:
      if "https" in item:
        parsed_url = urlparse(item)
        path = parsed_url.path
        url_id = path.split("/")[-1]
        if url_id not in uni_new_list:
          uni_new_list.add(url_id)
          _list.append(item)
      else:
        if item not in uni_new_list:
          uni_new_list.add(item)
          _list.append(item)
    return _list




  def _TWstandardtime(self):

    TAIPEI_TZ = ZoneInfo("Asia/Taipei")
    now_with_tz = datetime.datetime.now(TAIPEI_TZ)
    today_date_str = now_with_tz.date().isoformat()
    return today_date_str


  def generate_URLs(self, url):
    self.url = url
    try:
      response = requests.get(self.url, self.headers)
      response.encoding = 'utf-8'  # 確保中文不亂碼
      soup = BeautifulSoup(response.text, 'html.parser')

      article_container = soup.find_all('div', class_='story__content')
      for article in article_container:
        link_tags = article.find_all("a")

        for link_tag in link_tags:
          if link_tag.select_one("time"):
            time = link_tag.select_one("time.rank__time").get_text()
            news_date = time.split(" ")[0].replace("/","-")


            if link_tag.get('data-content_level') == "開放閱讀" and news_date == self._TWstandardtime() and "edn_maintab_cate" not in link_tag.get("href"):
              news_title = link_tag.select_one("h3.story__headline").get_text().strip()
              self.title_list.append(news_title)
              url = "https://money.udn.com/" + link_tag.get('href')
              self.url_list.append(url)

      self.title_list = self._generate_uni_news_list(self.title_list)
      self.url_list = self._generate_uni_news_list(self.url_list)

      if len(self.url_list) == len(self.title_list):
        if len(self.url_list) == 0:
          raise Exception("此專區今日尚無新聞")
        else:
          return self.url_list, self.title_list

      else:
        raise Exception("連結數與標題數不相同")

    except Exception as e:
      return(f"出現問題: {e}")


  def _extract_image(self, response):

    soup = BeautifulSoup(response.text, 'html.parser')
    try:
      if soup.figure:
        target_img = soup.select_one(".article-image a")
        if target_img and target_img.get('href'):
          print("抓取到圖片")
          return target_img['href']
        
      print("此新聞無照片，使用預設圖")
      return self.DEFAULT_IMAGE

    except Exception as e:
      print(f"error occured: {e}")
      return self.DEFAULT_IMAGE

  def _extract_keywords(self, response):
    try:
        soup = BeautifulSoup(response.text, 'html.parser')
        keywords_list = []
        # 1. 使用 CSS Selector 抓取所有關鍵字連結
        keyword_tags = soup.select(".article-keyword__item a")
        

        for tag in keyword_tags:
            # 2. 提取文字並去除空白
            text = tag.get_text().strip()
            if text and (text not in keywords_list):
              keywords_list.append(text)
        
        # print 檢查一下
        print(f"抓取到的關鍵字: {keywords_list}")
        
        # 3. 回傳列表 (例如: ['勞動基金', '股市', ...])
        return keywords_list

    except Exception as e:
        print(f"keyword_error: {e}")
        return []

  def _extract_article_content(self, response):
    soup = BeautifulSoup(response.text, 'html.parser')

    # 1. 鎖定最核心的文章容器
    article_container = soup.find('section', id='article_body')
    if not article_container:
        article_container = soup.select_one('.article-body__editor')

    if article_container:
        # 2. 定義要刪除的「雜物」選取器清單
        junk_selectors = [
            '.edn-ads--inlineAds',       # 廣告
            '.article-body__social-bar', # 社交分享按鈕
            '.article-keyword',          # 關鍵字標籤
            '.article-length',           # 本文共xx字
            '.article-body__time',       # 時間
            '.article-body__info',       # 記者資訊
            '.further-reading',          # 延伸閱讀區塊
            'audio',                     # 音訊標籤
            '.mp',                       # 播放器控制列
            'script',                    # 腳本
            'style'                      # 內嵌樣式
        ]

        # 執行大掃除：移除不必要的標籤
        for selector in junk_selectors:
            for junk in article_container.select(selector):
                junk.decompose()

        # 3. 處理「文中延伸閱讀」連結 (<li> 或 <p> 包裹的連結)
        for reading_link in article_container.find_all('a', {'data-slotname': 'list_文中延伸閱讀'}):
            # 優先刪除包裹它的父標籤，避免留下空的 <li> 或 <p>
            parent = reading_link.find_parent(['p', 'li'])
            if parent:
                parent.decompose()
            else:
                reading_link.decompose()

        # 4. 清理剩餘的 <p> 標籤屬性
        for p in article_container.find_all('p'):
            p.attrs = {}  # 移除所有屬性 (例如 style, class)
            
            # 如果 <p> 標籤內完全沒有內容或只有空白，則移除該標籤
            if not p.get_text(strip=True):
                p.decompose()

        # 5. 取得 HTML 字串內容
        final_html = article_container.decode_contents()

        # 6. 正則表達式清理：移除所有 HTML 註釋 (如 , )
        # r'' 是比對註釋的標準寫法
        final_html = re.sub(r'', '', final_html)

        # 7. 最後清理：移除多餘的換行與頭尾空白
        final_html = "".join(final_html.splitlines()) # 這會移除所有類型的換行並合併字串
        
        return final_html.strip()

    return "❌ 找不到文章內容"



  def news_crawler(self):

    try:
      for  i, url in enumerate(self.url_list):
        print(f"\n------開始抓取第{i+1}筆新聞------\n")
        response1 = requests.get(url, headers=self.headers)
        response1.encoding = 'utf-8'  # 確保中文不亂碼
        # 獲取網頁內容
        if response1.status_code != 200:

          raise requests.exceptions.RequestException(f"Request failed with status code {response1.status_code}")
        else:
          time.sleep(1)

          content = self._extract_article_content(response1)
          keywords = self._extract_keywords(response1)
          self.keywords_list.append(keywords)
          if content is None:
            print("\n------沒抓到文章...------\n")
            return None
          else:
            image = self._extract_image(response1)

            self.content_list.append(content)
            if image:
              self.image_list.append(image)
            else:
              print("error occured. no image, append DEFAULT IMAGE.")
              self.image_list.append(image)
          print(f"\n------第{i+1}筆新聞抓取完成------\n")

      return self.content_list, self.image_list, self.keywords_list
    except requests.exceptions.RequestException as e:
      print(f"\n------連線失敗...錯誤為:{e}------\n")
      return None


  def store_news(self):

    if len(self.title_list) == len(self.url_list) == len(self.content_list):
      for t, u, c in zip(self.title_list, self.url_list, self.content_list):
        self.all_news_list.append(
            {
              "id": len(self.all_news_list),
              "title": t,
              "url": u,
              "content": c
            })
        
    json.dump(self.all_news_list, open("news_data.json", "w", encoding="utf-8"), ensure_ascii=False)
    return self.all_news_list

  def temporary_storage_news(self):

    if len(self.title_list) == len(self.url_list) == len(self.content_list):
      for t, u, c in zip(self.title_list, self.url_list, self.content_list):
        self.all_news_list.append(
            {
              "id": len(self.all_news_list),
              "title": t,
              "url": u,
              "content": c
            })
    return self.all_news_list

  def update_news(self):
    title_set = set(self.title_list)
    url_set = set(self.url_list)
    new_title_item = title_set - self.history_title_list
    new_url_item = url_set - self.history_url_list
    self.history_title_list.update(title_set)
    self.history_url_list.update(url_set)
    print(self.history_title_list, self.history_url_list)



if __name__ == "__main__":
  url = "https://money.udn.com/money/cate/11111?from=edn_navibar"

  headers = {
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
      'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
      'Accept-Language': 'zh-TW,zh;q=0.8,en-US;q=0.5,en;q=0.3',
      'Referer': 'https://money.udn.com/'
    }

  #News_Crawler = NewsCrawler(headers)
  #News_Crawler.generate_URLs(url=url)
  #print(News_Crawler.url_list)
  #News_Crawler.news_crawler()
  #News_Crawler.store_news()
  #News_Crawler.update_news()
  #print(News_Crawler.all_news_list)


