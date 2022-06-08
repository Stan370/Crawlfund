from urllib.request import urlopen
import requests
url = "http://www.baidu.com"
resp = urlopen(url)
#print(resp.read())
open("" ,encoding='utf-8')
headers = {

}
resp1 = requests.get("https://www.baidu.com/s?wd=jay")
print(resp1.text)