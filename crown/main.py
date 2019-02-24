from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import argparse
import requests
import re
import json
import csv

login_url = 'http://www.pss-system.gov.cn/sipopublicsearch/portal/uilogin-forwardLogin.shtml'
login_code_url = 'http://www.pss-system.gov.cn/sipopublicsearch/portal/login-showPic.shtml'
login_check_url = 'http://www.pss-system.gov.cn/sipopublicsearch/wee/platform/wee_security_check'
cookies_file = "cookies.json"

search_url = 'http://www.pss-system.gov.cn/sipopublicsearch/patentsearch/executeTableSearch0529-executeCommandSearch.shtml'
search_page_url = 'http://www.pss-system.gov.cn/sipopublicsearch/patentsearch/showSearchResult-startWa.shtml'

request_header = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_4)'
                  ' AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
    'Accept-Encoding': 'gzip, deflate',
    'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
    'Connection': 'keep-alive'
}

abview_pattern = r"(?<=num=\"0001\">).+?(?=</base:Paragraphs>)"

store_dir = 'store'
csv_header = ['ID',
              'TIVIEW',     # 名称
              'ABVIEW',     # 简介
              # 'INVIEW',     # 发明人
              ]

def save_cookies(cookies_jar):
    with open(cookies_file, 'w') as f:
        json.dump(cookies_jar, f)


def load_cookies():
    with open(cookies_file, 'r') as f:
        return json.load(f)


def get_cookies():
    file_cookies = None
    if os.path.exists(cookies_file):
        file_cookies = load_cookies()
    login_code_resp = requests.get(login_code_url,
                                   headers=request_header,
                                   cookies=file_cookies)
    if requests.utils.dict_from_cookiejar(login_code_resp.cookies)['IS_LOGIN'] == 'true':
        return file_cookies

    with open("valcode.png", 'wb') as f:
        f.write(login_code_resp.content)
    code = input('请输入验证码: ')

    data = {
        'j_loginsuccess_url': '',
        'j_validation_code': str(code),
        'wee_remember_me': 'on',
        'j_username': 'Y3Jvd24wMTYyMQ==',
        'j_password': 'MTY4NTEuNWNyb3du'
    }

    login_check_resp = requests.post(login_check_url,
                                     data=data,
                                     headers=request_header,
                                     cookies=login_code_resp.cookies)

    # save the cookies
    new_cookies = requests.utils.dict_from_cookiejar(login_code_resp.cookies)
    for (k, v) in requests.utils.dict_from_cookiejar(login_code_resp.cookies).items():
        new_cookies[k] = v
    new_cookies['wee_username'] = 'Y3Jvd24wMTYyMQ%3D%3D'
    new_cookies['wee_password'] = 'MTY4NTEuNWNyb3du'
    save_cookies(new_cookies)

    return new_cookies


def extract_abview(row):
    if row is None:
        return re.findall(abview_pattern, row['ABVIEW'], re.I | re.S | re.M)[0]
    else:
        return None


def save_as_csv(rows, f):
    for row in rows:
        result = {'ID': row['ID'],
                  'ABVIEW': extract_abview(row),
                  'TIVIEW': row['TIVIEW']
                  }
        f.writerow(result)


# search the company pss info
def search_company_info(company, cookies, apply_date='20100101:20181231'):
    data = {
        'searchCondition.searchExp': '申请日=%s AND 申请（专利权）人=(%s)' %
                                     (apply_date, company),
        'searchCondition.dbId': 'VDB',
        'searchCondition.searchType': 'Sino_foreign',
        'searchCondition.sortFields': '-APD,+PD',
        'resultPagination.limit': '0',
        "searchCondition.extendInfo['MODE']": 'MODE_SMART',
        "searchCondition.extendInfo['STRATEGY']": "STRATEGY_CALCULATE",
    }

    search_header = request_header.copy()
    search_header['Content-Type'] = 'application/x-www-form-urlencoded; charset=UTF-8'
    search_header['Accept'] = 'application/json, text/javascript, */*; q=0.01'

    search_company_resp = requests.post(search_page_url,
                                        data=data,
                                        headers=search_header,
                                        cookies=cookies)
    # print(json.dumps(json.loads(search_company_resp.text), indent=4))

    # fetch each page and store to csv file
    company_info = json.loads(search_company_resp.text, encoding='utf-8')
    company_record_total_count = int(company_info['resultPagination']['totalCount'])

    count = 0
    data['resultPagination.limit'] = 12

    # check file exits and delete it
    filename = store_dir + '/' + company + '.csv'
    if os.path.exists(filename):
        os.remove(filename)

    with open(filename, 'w') as f:
        csv_f = csv.DictWriter(f, csv_header)
        csv_f.writeheader()
        while count < company_record_total_count:
            # fetch the record and save to csv
            data['resultPagination.start'] = count
            search_page_records_resp = requests.post(search_page_url,
                                    data=data,
                                    headers=search_header,
                                    cookies=cookies)
            page_result = json.loads(search_page_records_resp.text, encoding='utf-8')
            rows = list(value['fieldMap'] for value in page_result['searchResultDTO']['searchResultRecord'])
            print("get rows: %s" % len(rows))
            save_as_csv(rows, csv_f)
            print("current count: %s" % count)
            count = count + 12


if __name__ == '__main__':
    # parser = argparse.ArgumentParser(description="crawl pss-system.gov.cn")
    # parser.add_argument("--file", type=str, required=False,
    #                     help="the csv file contains a list of companies")
    # parser.add_argument("--company", type=str, required=False, default=None,
    #                     help="if defined, just crawl the single company")
    #
    # parser.add_argument("--store", type=str, required=False, default="./out",
    #                     help="the directory for csv files to store")
    #
    # args = parser.parse_args()

    # login_resp = requests.get(login_url)

    cookies = get_cookies()
    # cookies = {
    #     'WEE_SID': 'ZYL7V4cd6cYItFcBMtUF3CLdp88lttvupJObHO0FoQwrPC3x5XBf!1566140800!-1189980894!1550405043997',
    #     'IS_LOGIN': 'true',
    #     'wee_username': 'Y3Jvd24wMTYyMQ%3D%3D',
    #     'wee_password': 'MTY4NTEuNWNyb3du',
    #     'JSESSIONID': 'ZYL7V4cd6cYItFcBMtUF3CLdp88lttvupJObHO0FoQwrPC3x5XBf!1566140800!-1189980894'
    # }

    print("cookies: %s" % cookies)

    print("logined into the system.")

    # creat store directory
    if not os.path.exists(store_dir):
        os.mkdir(store_dir)

    # query pss
    search_company_info("北方工业大学", cookies)

