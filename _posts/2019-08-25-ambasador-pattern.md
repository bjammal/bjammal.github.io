---

layout: post
title: Hands-On Ambassador Pattern

---

In Brendan Burns' *Designing Distributed Systems* book, he gives an example on using the *ambassador pattern* for an experimentation case. The example is about request splitting, meaning distributing the request load between two versions of an application aiming at ensuring the proper functionality of the newer version by testing it under production workload. Although very useful, the hands-on only focuses on the pattern itself and provides the configuration of ambassador.

I wanted to try it myself. So, in this post I am complementing the example in the book with a simple client/server application and sharing with you the deployment and configuration I have done to experiment with this pattern. 

### A Recap on Ambassador Pattern

Using Ambassador Pattern, "an ambassador container brokers interactions between the application container and the rest of the world" [Brendan Burns, Designing Distributed Systems]. There are many use cases for this pattern. For instance, we can use it as a proxy to hide the complexity of communication with external services. An application would only care about one single connection to localhost on a specific port (provided by the ambassador), regardless of the type or number of data exchange that happen beyond this point. This modular system design allows us to keep the main application code simple, and to build a generic ambassador that can be reused with other applications as well. 

[Microsoft's article](https://docs.microsoft.com/en-us/azure/architecture/patterns/ambassador) explaining the pattern represents it with the following schema:

![Diagram of the Ambassador pattern](https://docs.microsoft.com/en-us/azure/architecture/patterns/_images/ambassador.png)

For more details and explanation refer to the article.

### Setup Overview

The setup we will use to demonstrate the pattern is illustrated here:

![](/home/bilal/Repositories/github/bjammal.github.io/img/ambassador-pattern.png)

- We have two versions of an application, each deployed in a Kubernetes pod.
- The client application is deployed as a container and shares the same pod with the ambassador container so that the former always has one single connection endpoint through localhost.
- The ambassador pattern receives the client requests and proxies them to v1 and v2beta servers and returns the response back to the client.

### Deploying the Main Application

Before using an ambassador we need to have the main application's service ready. In this example, I will use an nginx web server. I will consider that v1 is a production service and v2beta is an experiment service.

To keep it simple, the only difference between the two versions is the h1 header in the body of the index.html home page. In the production service it is going to be `<h1>This is your NGINX Production</h1>` and in the experiment service we will have `<h1>This is your NGINX Experiment</h1>`. So, the first thing is to create those two index pages that we will inject later in our nginx pods via a ConfigMap.

Create the experiment index file `nginx-experiment.html`:

```html
<!DOCTYPE html>
<html>
<head>
<title>Welcome to nginx!</title>
<style>
    body {
        width: 35em;
        margin: 0 auto;
        font-family: Tahoma, Verdana, Arial, sans-serif;
    }
</style>
</head>
<body>
<h1>This is your NGINX Experiment</h1>
</body>
</html>
```

Create the production index file `nginx-production.html`:

```html
<!DOCTYPE html>
<html>
<head>
<title>Welcome to nginx!</title>
<style>
    body {
        width: 35em;
        margin: 0 auto;
        font-family: Tahoma, Verdana, Arial, sans-serif;
    }
</style>
</head>
<body>
<h1>This is your NGINX Production</h1>
</body>
</html>
```

Create the two ConfigMaps using the following commands:

```shell
# create the experiment configmap
$ kubectl create configmap nginx-exp --from-file nginx-experiment.html
# create the production configmap
$ kubectl create configmap nginx-prod --from-file nginx-production.html
```

We are using a ConfigMap with `--from-file` flag. In this way, the name of the file will become a key in the configmap, and we can then use a volume mounting inside the pod to have this file at the mounting path.

Next, you can deploy the two nginx servers using a Deployment. To do this, first create the deployment file `nginx-dep.yaml` as follows:

```yaml
apiVersion: apps/v1 
kind: Deployment
metadata:
  name: nginx-prod
spec:
  selector:
    matchLabels:
      app: nginx-prod
  replicas: 1 
  template:
    metadata:
      labels:
        app: nginx-prod
    spec:
      containers:
      - name: nginx
        image: nginx:1.7.9
        ports:
        - containerPort: 80
        volumeMounts:
        - name: index
          mountPath: /usr/share/nginx/html
      volumes:
      - name: index
        configMap:
          name: nginx-prod
          items:
          - key: nginx-production.html
            path: index.html
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-exp
spec:
  selector:
    matchLabels:
      app: nginx-exp
  replicas: 1
  template:
    metadata:
      labels:
        app: nginx-exp
    spec:
      containers:
      - name: nginx
        image: nginx:1.7.9
        ports:
        - containerPort: 80
        volumeMounts:
        - name: index
          mountPath: /usr/share/nginx/html
      volumes:
      - name: index
        configMap:
          name: nginx-exp
          items:
          - key: nginx-experiment.html
            path: index.html
```

The  default location of the index page in the official nginx docker image is `/usr/share/nginx/html` so this is where we want our `mountPath` to be. The second thing to notice is that using the `path` element in the configMap volume we are changing the name of the file which takes its value by default from the configMap's key to `index.html`. 

Create the deployments with the command `kubectl create -f nginx-dep.yaml`. 

The final step is to create the services that expose the pods and, most importantly, create DNS names for the production and experiment application servers. We need the DNS names so we can use them later in the ambassador configuration to proxy requests. You can do this from the command line or by creating manifest files and using the `kubectl create -f` command. I will choose the former way because it is faster:

```shell
# create the experiment service
$  kubectl expose deploy nginx-exp --port 80 --protocol "TCP"
# create the production service
$  kubectl expose deploy nginx-prod --port 80 --protocol "TCP"
```

At this point, the two version service application are ready.

### Deploying The Client and The Ambassador

For the ambassador, we will use nginx as a load balancer this time and not as a web server. This is done by changing the nginx configuration. Once again, we will store the nginx configuration in a file and pass it to the pod using a ConfigMap. Here is the `nginx.conf` file I used:

```json
worker_processes 5;
worker_rlimit_nofile 8192;

events {
  worker_connections 1024;
}

http {
  upstream backend {
    server nginx-prod weight=8;
    server nginx-exp;
  }

  server {
    listen 80;
    location / {
      proxy_pass http://backend;
    }
  }
}
```

Notice that the name of the servers correspond to the name of the services we created (which in turn is inherited from the name of the deployment in our case).

Now, we will create a Pod consisting of two containers: the nginx ambassador and a client that we will use to request the home page of our service application with `curl` commands. Here's how the Pod manifest file looks like:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: ambassador-pattern
spec:
  containers:
  - name: nginx
    image: nginx
    volumeMounts:
    - name: config-volume
      mountPath: /etc/nginx
    securityContext:
      privileged: true
  - name: debug
    image: fabriziopandini/debug
  volumes:
  - name: config-volume
    configMap:
      name: nginx-conf
```

Save it to `ambassador.yaml` and create it with `kubectl create -f ambassador.yaml`. Once running, log into the debug container shell and enter the `curl localhost:80` command, or simply use `kubectl exec` as in the below example. 80% of the time you should see *This is your NGINX Production* in the response, and the remaining 20% of the responses should be *This is your NGINX Experiment*.

```shell
$ kubectl exec ambassador-pattern -c debug -- curl localhost:80
<!DOCTYPE html>
<html>
<head>
<title>Welcome to nginx!</title>
<style>
    body {
        width: 35em;
        margin: 0 auto;
        font-family: Tahoma, Verdana, Arial, sans-serif;
    }
</style>
</head>
<body>
<h1>This is your NGINX Production</h1>

<p>For online documentation and support please refer to
<a href="http://nginx.org/">nginx.org</a>.<br/>
Commercial support is available at
<a href="http://nginx.com/">nginx.com</a>.</p>

<p><em>Thank you for using nginx.</em></p>
</body>
</html>

$ kubectl exec ambassador-pattern -c debug -- curl localhost:80
<!DOCTYPE html>
<html>
<head>
<title>Welcome to nginx!</title>
<style>
    body {
        width: 35em;
        margin: 0 auto;
        font-family: Tahoma, Verdana, Arial, sans-serif;
    }
</style>
</head>
<body>
<h1>This is your NGINX Experiment</h1>
</body>
</html>
```

### Summary

In this post we used ambassador pattern to split requests between two versions of a service. We deployed the ambassador container at the client side with the client container in the same pod. This allows them to share the network namespace and communicate via localhost.

