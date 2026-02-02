from bs4 import BeautifulSoup
from pathlib import Path
from urllib.parse import urlparse
import json
import requests
import time
import datetime
import pytz
from zoneinfo import ZoneInfo

class NewsCrawler:
  def __init__(self, headers):

    self.url = ""
    self.headers = headers
    self.url_list = []
    self.title_list = []
    self.content_list = []
    self.image_list = []
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


  def _extract_news_image(self, response):

    soup = BeautifulSoup(response.text, "html.parser")
    try: 
      if soup.figure: 
        target_img = soup.select_one(".article-image a")
        if target_img and target_link.get('href'):
          print("抓取到圖片 (data-srcset)")
          return target_img['data-srcset']
        
      print("此新聞無圖片，使用預設圖")
      return self.DEFAULT_IMAGE

    except Exception as e:
      print(f"image_error: {e}")
      return self.DEFAULT_IMAGE

  def _extract_article_content(self, response):

    # 1. 先給一個預設值，確保變數一定存在
    news_title = "無標題"
    
    soup = BeautifulSoup(response.text, 'html.parser')

    # 2. 嘗試抓取並覆蓋預設值
    if soup.title and soup.title.string:
        news_title = soup.title.string.strip() # 建議加上 strip() 去除前後空白
    else:
        print("未抓到網頁標題 tag")

    # 3. 現在無論上面走哪條路，news_title 都一定有值，print 就不會報錯了
    print(f"新聞標題: {news_title}", flush=True)
    
    # --- 以下維持原本邏輯 ---
    article_container = soup.select_one('section.article-body__editor, section.article-body')

    if article_container is None:
        print("!!! 警告：找不到文章內容容器 !!!", flush=True)
        return None # 建議回傳 None 讓呼叫端知道失敗

    elif article_container:

        # 找到容器內所有 <p> 標籤
      paragraphs = article_container.find_all('p')

        # 提取文字並合併
      article_text = []

      for p in paragraphs:
        text = p.get_text().strip()

            # 過濾掉可能存在的空行或廣告文字

        if text and not text.startswith("※"):
            article_text.append(text)

        # 合併成一個乾淨的長字串

      final_article = '\n\n'.join(article_text)

      if len(final_article) == 0:
        print("沒抓到文章")

      else:
        return final_article

  def news_crawler(self):
    print(f"準備開始抓取 {len(self.url_list)} 筆新聞...")
        
    for i, url in enumerate(self.url_list):
      print(f"\n------開始抓取第 {i+1} 筆新聞------")
      try:
        response = requests.get(url, headers=self.headers, timeout=10) # 建議加上 timeout
                
        if response.status_code != 200:
          print(f"請求失敗: {response.status_code}")
          continue # 跳過這一筆，繼續下一筆

          # 建立 Soup 物件 (只要建一次就好，傳給下面函式用)
        soup = BeautifulSoup(response.text, 'html.parser')

        # 1. 抓內容
        content = self._extract_article_content(soup)
                
        # 2. 抓圖片 (即使內容沒抓到，也可以考慮要不要抓圖，但通常沒內容就跳過)
        if content:
          image = self._extract_news_image(soup)
                    
          # 存入列表 (確保成對存入)
          self.content_list.append(content)
          self.image_list.append(image)
          print(f"✅ 第 {i+1} 筆成功入庫")
        else:
          print(f"❌ 第 {i+1} 筆失敗：無內容")

          time.sleep(1) # 禮貌性延遲

      except Exception as e:
        print(f"抓取過程發生錯誤: {e}")
        continue

    print("\n所有新聞抓取完成！")
    return self.content_list, self.image_list

  """def news_crawler(self):

    try:
      for  i, url in enumerate(self.url_list):
        print(f"\n------開始抓取第{i+1}筆新聞------\n")
        response1 = requests.get(url, self.headers)
        response1.encoding = 'utf-8'  # 確保中文不亂碼
        # 獲取網頁內容
        if response1.status_code != 200:

          raise requests.exceptions.RequestException(f"Request failed with status code {response1.status_code}")
        else:
          time.sleep(1)

          image = self._extract_news_image(response1)
          content = self._extract_article_content(response1)
          if content is None:
            print("\n------沒抓到文章...------\n")
            return None
          else:
            if image not None:
              self.image_list.append(image)
              self.content_list.append(content)
            else:
              print("沒抓到照片")

            print(f"\n------第{i+1}筆照片、新聞抓取完成------\n")

      return self.content_list, self.image_list
    except requests.exceptions.RequestException as e:
      print(f"\n------連線失敗...錯誤為:{e}------\n")
      return None
"""

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
  #url = "https://money.udn.com/money/cate/11111?from=edn_navibar"

  headers = {
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
      'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
      'Accept-Language': 'zh-TW,zh;q=0.8,en-US;q=0.5,en;q=0.3',
      'Referer': 'https://money.udn.com/'
    }

  News_Crawler = NewsCrawler(headers)
  News_Crawler.generate_URLs(url=url)
  print(News_Crawler.url_list)
  #News_Crawler.news_crawler()
  #News_Crawler.store_news()
  #News_Crawler.update_news()


