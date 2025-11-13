import json

class News:
  def __init__(self, source_type: str):

    self.source_dict = {
        "要聞": "https://money.udn.com/money/cate/10846?from=edn_navibar",
        "產業": "https://money.udn.com/money/cate/5591?from=edn_navibar",
        "證券": "https://money.udn.com/money/cate/5590?from=edn_navibar",
        "國際": "https://money.udn.com/money/cate/5588?from=edn_navibar",
        "金融": "https://money.udn.com/money/cate/12017?from=edn_navibar",
        "期貨": "https://money.udn.com/money/cate/11111?from=edn_navibar",
        "理財": "https://money.udn.com/money/cate/5592?from=edn_navibar",
        "房市": "https://money.udn.com/money/cate/5593?from=edn_navibar",
        "專欄": "https://money.udn.com/money/cate/5595?from=edn_navibar",
        "專題": "https://money.udn.com/money/cate/123428?from=edn_navibar",
        "商情": "https://money.udn.com/money/cate/5597?from=edn_navibar",
        "兩岸": "https://money.udn.com/money/cate/5589?from=edn_navibar"}

    self.source_url = self.source_dict[source_type]


