import re

#findall匹配字符串中所有内容
lst = re.findall(r"\d+","100103123,10086")
print(lst)
it = re.finditer()
for i in it:
    print(it.group())
#search 返回第一个match对象
se = re.search()
#.match()从头匹配
