import time
from bs4 import BeautifulSoup
import requests
import re
import json
import streamlit as st

import openai

openai.api_key = 'OPEN-API-KEY'  # api key 입력
URL = "https://api.openai.com/v1/chat/completions" # gpt url

#-----Naver News 크롤링
def get_article_content(url):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/98.0.4758.102"}
    news = requests.get(url, headers=headers)
    news_html = BeautifulSoup(news.text, "html.parser")

    # 뉴스 제목 가져오기
    title = news_html.select_one("#ct > div.media_end_head.go_trans > div.media_end_head_title > h2")
    if title == None:
        title = news_html.select_one("#content > div.end_ct > div > h2")

    # 뉴스 본문 가져오기
    content = news_html.select("div#dic_area")
    if content == []:
        content = news_html.select("#articeBody")

    # 기사 텍스트만 가져오기
    content = ''.join(str(content))

    # html태그제거 및 텍스트 다듬기
    pattern1 = '<[^>]*>'
    title = re.sub(pattern=pattern1, repl='', string=str(title))
    content = re.sub(pattern=pattern1, repl='', string=content)
    pattern2 = """[\n\n\n\n\n// flash 오류를 우회하기 위한 함수 추가\nfunction _flash_removeCallback() {}"""
    content = content.replace(pattern2, '')

    try:
        html_date = news_html.select_one(
            "div#ct> div.media_end_head.go_trans > div.media_end_head_info.nv_notrans > div.media_end_head_info_datestamp > div > span")
        news_date = html_date.attrs['data-date-time']
    except AttributeError:
        news_date = news_html.select_one("#content > div.end_ct > div > div.article_info > span > em")
        news_date = re.sub(pattern=pattern1, repl='', string=str(news_date))

    return title, content, news_date

#-----기사 자르기
def split_text(text, chunk_size):
    return [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]

#-----chat gpt 이용
def gpt_api(content, text):
    payload = {
        "model": "gpt-3.5-turbo",
        "messages": [{"role": "user",
                      "content": content + "기사: " + text
                      }],
        "temperature": 0.6,
        "top_p": 1.0,
        "n": 1,
        "stream": False,
        "presence_penalty": 0,
        "frequency_penalty": 0,
    }
    return payload

#-----keyword 추출
def extract_keyword(text):
    keyword_content = "[아래의 기사]에서 핵심 단어를 5가지 뽑아주세요. 결과는 python의 list 형태로 알려주세요\n"

    payload = gpt_api(keyword_content, text)

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {openai.api_key}"
    }

    response = requests.post(URL, headers=headers, json=payload, stream=False)
    resp = json.loads(response.content)
    print(resp)
    time.sleep(25)

    return resp['choices'][0]['message']['content']

#-----조건에 맞춰 해당하는 단어 추출
def news_filterling(select, text_chunks):


    results = []

    guess_content = "추측성 단어는 글의 저자가 확신을 가지고 주장하지 않고 추측이나 예상에 기반하여 이야기하는 단어나 표현을 말합니다." \
                    "추측성 단어는 가능성이나 추측을 나타내는 단어, 조건부나 가정적인 표현, 주관적인 표현입니다." \
                    "추측성 단어의 예시로는 예측, 추측, 가능성, 아마, 어쩌면, 상당히, 거의 확실하게, 아마도 등과 같은 단어들이 있습니다." \
                    "추측성 표현의 예시로는  ~이면, ~라면, ~것 같다, ~인 것 같다, ~할 수도 있다 등과 같은 표현들이 있습니다." \
                    "주관적인 표현의 예시로는 생각에는, 느낀 바로는, 개인적으로 등과 같은 표현이 있습니다."  \
                    "[아래의 기사]에서 추측성 단어를 찾고 python의 list 형태로 만들어주세요." \
                    "추측성 단어가 없으면 '없음'이라고만 답변하세요.\n" \

    incentive_content = "자극적인 단어는 감정이나 강한 표현을 포함하고 있어 독자의 관심을 끌거나 주장을 강화하는 역할을 합니다." \
                        "자극적인 단어는 강한 감정을 일으킬 수 있는 단어, 강조나 비교에 사용되는 단어, 강렬한 이미지를 상상케 하는 단어입니다." \
                        "그 예시로는 충격적인, 파격적인, 강렬한, 끔찍한, 아비규환, 최대, 최고, 절대적으로, 상당히, 극도로 등이 있습니다." \
                        "[아래의 기사]에서 자극적인 단어를 찾고 python의 list 형태로 만들어주세요." \
                        "자극적인 단어가 없으면 '없음'이라고만 답변하세요.\n" \


    for text in text_chunks:
        if select == "추측성 단어":
            payload = gpt_api(guess_content, text)
        else:
            payload = gpt_api(incentive_content, text)

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {openai.api_key}"
        }

        response = requests.post(URL, headers=headers, json=payload, stream=False)
        resp = json.loads(response.content)
        print(resp)
        results.append(resp['choices'][0]['message']['content'])
        time.sleep(25)

    return results

#-----기사 요약
def news_summay(text, title):
    summary_content = f"[아래의 기사]의 내용을 번호를 매겨 3줄로 요약해주세요. [아래의 기사] 제목은 {title}입니다."

    payload = gpt_api(summary_content, text)

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {openai.api_key}"
    }

    response = requests.post(URL, headers=headers, json=payload, stream=False)
    resp = json.loads(response.content)
    print(resp)
    time.sleep(25)

    return resp['choices'][0]['message']['content']


#-----해당하는 단어 강조
def highlight_keywords(text, keywords, select):
    for word in keywords:
        if select == "추측성 단어":
            text = text.replace(word, f"<span style='color:red; font-weight:bold'>{word}</span>")
        elif select == "자극적인 단어":
            text = text.replace(word, f"<span style='color:blue; font-weight:bold'>{word}</span>")
    return text


def main():
    st.set_page_config(layout="wide")

    news_url = st.text_area("URL 입력", "")
    options = ['추측성 단어', '자극적인 단어']
    select = st.radio("옵션을 선택하세요", options)

    try:
        # 기사 크롤링
        news_title, news_content, news_date = get_article_content(news_url)

        # 기사 키워드
        st.header("기사 키워드")
        news_keyword = extract_keyword(news_content)
        st.write(news_keyword)
        print(type(news_keyword))

        col1, col2 = st.columns(2)

        with col1:
            # 원본 기사
            st.header("기사 분석")
            st.subheader(news_title)
            st.subheader(news_date)
            st.write(news_content)

        with col2:
            # 기사 쪼개기
            chunk_size = 300
            text_chunks = split_text(news_content, chunk_size)

            # 조건에 해당하는 단어 만들기
            response = news_filterling(select, text_chunks)


            filter_words = []

            for item in response:
                if item.startswith("["):
                    item_list = eval(item)  # 문자열을 리스트로 변환
                    filter_words.extend(item_list)
                else:
                    item = item.replace("'", "")  # 작은 따옴표 제거
                    filter_words.append(item)

            # 기사 시각화
            st.subheader(news_title)
            st.subheader(news_date)
            print(filter_words)

            highlighted_text = highlight_keywords(news_content, filter_words, select)
            st.markdown(highlighted_text, unsafe_allow_html=True)

        st.header("3줄 요약")
        st.write(news_summay(news_content, news_title))

    except requests.exceptions.MissingSchema:
        pass


if __name__ == '__main__':
    main()
