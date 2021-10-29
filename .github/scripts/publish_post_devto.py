import requests
import json
import sys, getopt
import os

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
    token = os.getenv('DEV_TO_TOKEN')
    header = {
        "Content-Type":	"application/json",
        "api-key"	: f"{token}"
    }

    url = "https://dev.to/api/articles"

    title, content, tags = get_post_data(file)
    post_name = file.split(".")[0]

    data = {
        "article": {
            "title": f"{title}",
            "published": False,
            "body_markdown": f"{content}",
            "canonical_url": f"https://bjammal.github.io/{post_name}/",
            "tags": tags,
        }
    }

    payload = json.dumps(data)
    response = requests.post(url, headers=header,data=payload)

    print(response.text)
    if response.status_code == 201:
        response_json = response.json()
        post_url = response_json["url"]
        print(f"The post is published at {post_url}")
    else:
        print(f"Status Code: {response.status_code}")
        print(response.text)

def main(argv):
    inputfile = ''
    try:
        opts, args = getopt.getopt(argv,"hi:",["ifile="])
    except getopt.GetoptError:
        print('publish_post_devto.py -i <inputfile>')
    for opt, arg in opts:
        if opt == '-h':
            print('publish_post_devto.py -i <inputfile>')
            sys.exit()
        elif opt in ("-i", "--ifile"):
            inputfile = arg

    publish(inputfile)

if __name__ == "__main__":
   main(sys.argv[1:])