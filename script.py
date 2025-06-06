from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import requests
from bs4 import BeautifulSoup
import csv
import numpy as np
import re
import time
import signal
import os
import sys


def ippungotojikkou():

    TOKYO_TO_NAGOYA = os.environ.get("TOKYO_TO_NAGOYA")
    TOKYO_TO_OSAKA = os.environ.get("TOKYO_TO_OSAKA")
    NAGOYA_TO_OSAKA = os.environ.get("NAGOYA_TO_OSAKA")
    NAGOYA_TO_TOKYO = os.environ.get("NAGOYA_TO_TOKYO")
    OSAKA_TO_TOKYO = os.environ.get("OSAKA_TO_TOKYO")
    OSAKA_TO_NAGOYA = os.environ.get("OSAKA_TO_NAGOYA")
    




    lock_file = "lock_file.lock"




    class TimeoutException(Exception):
      pass

    def handler(signum, frame):
      raise TimeoutException()

    def ippungoto():

      driver = None

      try:
        signal.signal(signal.SIGALRM, handler)
        signal.alarm(50)  # 50秒のタイムアウト設定


        url = "https://cp.toyota.jp/rentacar/?padid=ag270_fr_sptop_onewayma"
        options = webdriver.ChromeOptions()
        options.add_argument("--headless") # or use pyvirtualdiplay
        options.add_argument("--no-sandbox") # needed, because colab runs as root

        #options.headless = True

        #ここから追加のオプション

        options.add_argument("start-maximized")
        options.add_argument("enable-automation")
        options.add_argument("--disable-infobars")
        options.add_argument('--disable-extensions')
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-browser-side-navigation")
        options.add_argument("--disable-gpu")
        options.add_argument('--ignore-certificate-errors')
        options.add_argument('--ignore-ssl-errors')
        prefs = {"profile.default_content_setting_values.notifications" : 2}
        options.add_experimental_option("prefs",prefs)

        #ここまで追加のオプション

        service = Service(executable_path='/usr/bin/chromedriver')

        driver = webdriver.Chrome(service=service, options=options)

        driver.get(url)


        html = driver.page_source.encode('utf-8')




        #☆借りれる車を配列にする。
        soup = BeautifulSoup(html, 'html.parser')
        # Find all the objects with class "service-item__body" but without class "show-entry-end"

        for tag in soup.findAll(class_="show-entry-end"):
            # show-entry-end（グレーアウトのやつ）の親要素から削除。（親要素で出発地、目的地がわかる）
            tag.parent.decompose()

        def search_and_notify(pref_start, pref_return, csv_file, discord_token):
          items = soup.find_all("li" , {"data-start-area" : pref_start, "data-return-area" : pref_return})
          #二次元配列にする
          items = [[item] for item in items]
          #半分にする
          items = items[:-(len(items)//2)]

          #書式をそろえるために、temp.csvに書き込み、読み取る。
          #書き込む
          with open("temp.csv", "w", newline="", encoding="utf-8") as csvfile:
              writer = csv.writer(csvfile)
              for item in items:
                  writer.writerow(item)
          #読み取る
          with open("temp.csv", "r", newline="", encoding="utf-8") as csvfile:
            reader = csv . reader ( csvfile )
            re_read_items = [ e for e in reader ]



          #☆古いデータと比べる
          #ラズパイでやるときは、その名前のCSVを用意して、「あ」とでも１文字最初に入れておけばいいな。
          with open(csv_file, "r", newline="", encoding="utf-8") as csvfile:
            reader = csv . reader ( csvfile )
            olddata = [ e for e in reader ]
            #増えたやつ（olddataになくてitemsにあるもの）
            new_items = [item for item in re_read_items if item not in olddata]
            #減ったやつ（olddataにあってitemsにないもの）
            lost_items = [item for item in olddata if item not in re_read_items]




            #☆　成型して通知
            #増えてるなら通知→全削除して書き換え　減ってるなら全削除して書き換え、　増減なしならそのまま
          # w：ファイルに新規で書き込みを行う（既存のファイルの中身は消される）


          if len(new_items) > 0:
            #new_itemsのデータ形成して通知
            #通知要の配列
            tosend = []
            for item in new_items:
              tempsoup  = BeautifulSoup(item[0], 'html.parser')
              for tag in tempsoup.findAll(class_="label-sp"):
                tag.decompose()

              #出発店舗を抽出 pで、親要素のクラスがservice-item__shop-start のやつ！
              shop_start = tempsoup.select_one(".service-item__shop-start").p.text.strip()
              #正規表現で、都道府県と店名を抽出
              #東京都その他で場合分け
              if "トヨタモビリティサービス " in shop_start:
                shop_start_pref = "東京"
              elif "トヨタS＆Dレンタシェア西東京" in shop_start:
                shop_start_pref = "西東京"
              elif "静岡トヨタ自動車" in shop_start:
                shop_start_pref = "※静岡"
              else:
                shop_start_pref = re.search(r'(トヨタレンタリース)(.+?)\s', shop_start).group(2)
              #店名
              shop_start_name = re.search(r'\s+(.+?)店', shop_start).group(1)

              #返却地域を抽出
              shop_return = tempsoup.select_one(".service-item__shop-return").p.text.strip()
              #東京都その他で場合分け
              if "トヨタモビリティサービス " in shop_return:
                shop_return_pref = "東京"
              elif "トヨタS＆Dレンタシェア西東京" in shop_return:
                shop_return_pref = "西東京"
              elif "静岡トヨタ自動車" in shop_return:
                shop_return_pref = "※静岡"
              else:
                shop_return_pref = re.search(r'(トヨタレンタリース)(.+?)\s', shop_return).group(2)
              #期間を抽出
              date = tempsoup.select_one(".service-item__date").p.text.strip()
              #車種を抽出
              car_type = tempsoup.select_one(".service-item__info__car-type").p.text.strip()
              pattern = r"^([\S]+?)(\s|$)"  # 正規表現パターン

              match = re.search(pattern, car_type)  # 正規表現パターンとマッチする部分を検索

              if match:
                  car_type = match.group(1)  # 1番目のキャプチャグループ（最初の文字から空白（全角または半角）まで）を取得
              else:
                  car_type = car_type
              #説明を抽出
              info = tempsoup.select_one(".service-item__info__condition").p.text.strip()
              #禁煙車、喫煙車、禁煙、喫煙を削除
              info.replace("禁煙車","")
              info.replace("喫煙車","")
              info.replace("禁煙","")
              info.replace("喫煙","")

              #電話番号を取得
              tel =  tempsoup.select_one(".service-item__reserve-tel").text.strip()
              #送信用に並び替えて送信用の配列に入れる
              tosend.append(f'{shop_start_pref} {shop_start_name}→{shop_return_pref}\n{car_type}{info}\n{date}\n{tel}\n.')

            #lineで通知する関数
            '''
            def line_notify(token,message):
              # 取得したTokenを代入
              line_notify_token = token

              # 送信したいメッセージ
              message =  message

              # Line Notifyを使った、送信部分
              line_notify_api = 'https://notify-api.line.me/api/notify'
              headers = {'Authorization': f'Bearer {line_notify_token}'}
              data = {'message': f'{message}'}
              requests.post(line_notify_api, headers=headers, data=data)
            '''
            #discordで通知する関数
            def discord_notify(url,msg):
              webhook_url = url
              message = msg

              data = {
                  "content": message
              }

              response = requests.post(webhook_url, json=data)

              if response.status_code == 204:
                  print("メッセージが正常に送信されました。")
              else:
                  print(f"メッセージの送信に失敗しました。 (エラーコード: {response.status_code})")

            #１つずつ通知する
            for item in tosend:
              #line_notify(sorezore_token,item)
              discord_notify(discord_token , item)



            #書き換え
            with open(csv_file, "w", newline="", encoding="utf-8") as csvfile:
              writer = csv.writer(csvfile)
              for item in items:
                  writer.writerow(item)

          elif len(lost_items) > 0:
            #書き換え
            print("減った")
            with open(csv_file, "w", newline="", encoding="utf-8") as csvfile:
              writer = csv.writer(csvfile)
              for item in items:
                  writer.writerow(item)


        #３関東　４中部　５関西

        search_and_notify(3,4,"東→名.csv", TOKYO_TO_NAGOYA)
        search_and_notify(3,5,"東→阪.csv", TOKYO_TO_OSAKA)
        search_and_notify(4,5,"名→阪.csv", NAGOYA_TO_OSAKA)
        search_and_notify(4,3,"名→東.csv", NAGOYA_TO_TOKYO)
        search_and_notify(5,3,"阪→東.csv", OSAKA_TO_TOKYO)
        search_and_notify(5,4,"阪→名.csv", OSAKA_TO_NAGOYA)

      except TimeoutException:
        print("Ippungoto function timed out")

      finally:
        signal.alarm(0)  # タイマーを解除
        if driver is not None:
          driver.quit()
          print("ドライバーを閉じた")

    # ロックファイルのチェックと作成
    if os.path.exists(lock_file):
      print("Another instance is running. Exiting.")
      sys.exit(0)

    try:
      # ロックファイルを作成
      with open(lock_file, "w") as lock:
            lock.write("locked")

      # ここでプログラムの処理を行う
      ippungoto()

    finally:
      # 成功またはタイムアウトが発生した場合、ロックファイルを削除
      os.remove(lock_file)


def main():
    ippungotojikkou()

if __name__ == "__main__":
    main()


