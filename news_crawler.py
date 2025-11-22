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
    self.all_news_list = []
    self.history_url_list = set()
    self.history_title_list = set()

  """def _generate_uni_news_list(self, any_list):
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
    return _list"""




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

      seen_url_ids = set() # 建立一個 Set 來記錄已處理的 URL ID，確保唯一性
      unique_news_data = [] # 建立一個 List of Tuples 來儲存 (URL, Title)，確保兩者對齊
      
      for article in article_container:
        link_tags = article.find_all("a")

        for link_tag in link_tags:
          if link_tag.select_one("time"):
            time = link_tag.select_one("time.rank__time").get_text()
            news_date = time.split(" ")[0].replace("/","-")


            if link_tag.get('data-content_level') == "開放閱讀" and news_date == self._TWstandardtime() and "edn_maintab_cate" not in link_tag.get("href"):
              news_title = link_tag.select_one("h3.story__headline").get_text().strip()
              #self.title_list.append(news_title)
              url = "https://money.udn.com/" + link_tag.get('href')
              #self.url_list.append(url)
              parsed_url = urlparse(url)
              url_id = parsed_url.path.split("/")[-1]

              if url_id not in seen_url_ids:
                seen_url_ids.add(url_id)
                unique_news_data.append((url,news_title))
      '''self.title_list = self._generate_uni_news_list(self.title_list)
      self.url_list = self._generate_uni_news_list(self.url_list)'''


      if len(unique_news_data) == 0:
        raise Exception("此專區今日尚無新聞")
      else:
        final_url_list, final_title_list = zip(*unique_news_data)

        self.url_list = list(final_url_list)
        self.title_list = list(final_title_list)
        return self.url_list, self.title_list

    except Exception as e:
      return(f"出現問題: {e}")





  def _extract_article_content(self, response):

    news_title_list = []

    soup = BeautifulSoup(response.text, 'html.parser')

    if soup.title:
      news_title = soup.title.string
      news_title_list.append(news_title)
    else:
      print("無標題")

    print(f"新聞標題: {news_title}", flush=True)
    article_container = soup.select_one('section.article-body__editor, section.article-body')

    if article_container is None:
        print("!!! 警告：找不到文章內容容器 !!!", flush=True)
        return

    # 3. 提取所有段落文字
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

    else:
        return("❌ 找不到文章內容的容器。您可能需要檢查網頁原始碼以取得正確的 CSS 選擇器。")



  def news_crawler(self):

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

          content = self._extract_article_content(response1)
          if content is None:
            print("\n------沒抓到文章...------\n")
            return None
          else:
            self.content_list.append(content)
          print(f"\n------第{i+1}筆新聞抓取完成------\n")

      return self.content_list
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

  def reset_lists(self):
    """ 清空所有內部列表以準備下一次爬取 """
    self.url_list = []
    self.title_list = []
    self.content_list = []

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



