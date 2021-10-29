import requests
import json
import sys, getopt
import os

def get_user_id():
    api_url = "https://api.medium.com/v1/me"
    header = {
        "Accept":	"text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Encoding"	:"gzip, deflate, br",
        "Accept-Language"	:"en-US,en;q=0.5",
        "Connection"	:"keep-alive",
        "Host"	:"api.medium.com",
        "TE"	:"Trailers",
        "Upgrade-Insecure-Requests":	"1"
    }
    token = os.getenv('MEDIUM_TOKEN')
    response = requests.get(api_url, headers=header, params={"accessToken": token})
    if response.status_code == 200:
        data = response.json()
        userId = data['data']['id']
    return userId

def get_post_data(file):
    title = ''
    content = ''
    tags = ''
    with open(file) as post:
        lines = post.readlines()
    
    #TO DO: try regex
    # Assumption: the first 5 lines of the file are as follows:
    # ---
    # layout: 
    # title: 
    # tags:
    # ---
    if lines[0] == "---\n":
        for line in lines[1:4]:
            if line[0:5] == "tags:":
                tags = line[5:].lstrip().rstrip("\n").split(" ")
            if line[0:6] == "title:":
                title = line[7:]

        for line in lines[5:]:
            content += line
        
        return title, content, tags
    else:
        print("The file format is not compliant to Jekyll front matter")
        exit(1)


def publish(file):
    token = os.getenv('MEDIUM_TOKEN')
    header = {
        "Accept":	"text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Encoding"	:"gzip, deflate, br",
        "Accept-Language"	:"en-US,en;q=0.5",
        "Connection"	:"keep-alive",
        "Host"	:"api.medium.com",
        "TE"	:"Trailers",
        "Authorization": f"Bearer {token}",
        "Upgrade-Insecure-Requests":	"1"
    }
    authorId = get_user_id()
    api_url = f"https://api.medium.com/v1/users/{authorId}/posts"

    title, content, tags = get_post_data(file)
    post_name = file.split(".")[0]

    data = {
        "title": f"{title}",
        "contentFormat": "markdown",
        "content": f"{content}",
        "canonicalUrl": f"https://bjammal.github.io/{post_name}/",
        "tags": tags,
        "publishStatus": "draft"   # "public" will publish, "draft" to save as draft
    }

    response = requests.post(api_url, headers=header,data=data)

    print(response.text)
    if response.status_code == 201:
        response_json = response.json()
        url = response_json["data"]["url"]
        print(f"The post is published at {url}")

def main(argv):
    inputfile = ''
    try:
        opts, args = getopt.getopt(argv,"hi:",["ifile="])
    except getopt.GetoptError:
        print('publish_post_medium.py -i <inputfile>')
    for opt, arg in opts:
        if opt == '-h':
            print('publish_post_medium.py -i <inputfile>')
            sys.exit()
        elif opt in ("-i", "--ifile"):
            inputfile = arg

    publish(inputfile)

if __name__ == "__main__":
   main(sys.argv[1:])