---
layout: post
tags: kubernetes API kubectl curl
title: "Understanding the Kubernetes API"
---

In the previous [post](https://bjammal.github.io/2019-05-28-kubernetes-cluster-access/), I showed how you can configure kubectl to authenticate to the Kubernetes API server with an external (system) user. I also mentioned that `kubectl` is only a CLI client that communicates with the API server using HTTP REST requests. In this post I want to show how we can explore the API and interact with it by sending REST requests without using kubectl.

### API Versioning

The k8s [documentation](https://kubernetes.io/docs/concepts/overview/kubernetes-api/) provides an extensive explanation of the versioning system the community uses for the API.

> Kubernetes supports multiple API versions, each at a different API path, such as `/api/v1` or `/apis/extensions/v1beta1`

In other words, the version is at the API group level (groups are explained in the next section). As the documentation states, different API versions imply different stability and support levels that are summarized as follows:

- Alpha level:  
  The version names contain `alpha` (e.g. `v1alpha1`). Resources of the groups having this version may contain bugs. This version is disabled by default. Changes to the API of this level may happen in a non-backward compatible way and the support for feature may be dropped at any time without notice.
- Beta level:  
  The version names contain `beta` (e.g. `v2beta3`). In this level, code is well tested and enabling the feature is considered safe, which is why it is enabled by default. Support for the overall feature will not be dropped, though details may change.
- Stable level:  
  The version name is `vX` where `X` is an integer. Stable versions of features will appear in released software for many subsequent versions.

Please refer to the [docs](https://kubernetes.io/docs/concepts/overview/kubernetes-api/) for detailed information.

### API Groups

The first and easiest way to get more information about the API that k8s exposes is to run the `curl https://<serverip>:<port>/apis -k` command. You can get the ip address and port of your API server by running `kubectl cluster-info`.  The API is organized in groups of endpoints to make the development and extension of each group independent. A group can be specified in two ways:

- in a REST path (URL) following the pattern `/apis/$GROUP_NAME/$VERSION`
- in an `apiVersion` field of a serialized object (YAML manifest files are serialized to JSON as we will see later) following the pattern `$GROUP_NAME/$VERSION`

> k8s [documentation](https://kubernetes.io/docs/reference/using-api/api-overview/): "The named groups are at REST path `/apis/$GROUP_NAME/$VERSION`, and use `apiVersion: $GROUP_NAME/$VERSION` (for example, `apiVersion: batch/v1`)."

If you examine the output of the previous `curl` command, you can see a list of groups started by the key "groups".

```shell
user@k8s-master$ curl https://127.0.0.1:6443/apis -k
{
  "kind": "APIGroupList",
  "apiVersion": "v1",
  "groups": [
    {
      "name": "apiregistration.k8s.io",
      "versions": [
        {
          "groupVersion": "apiregistration.k8s.io/v1",
          "version": "v1"
        },
        {
          "groupVersion": "apiregistration.k8s.io/v1beta1",
          "version": "v1beta1"
        }
      ],
      "preferredVersion": {
        "groupVersion": "apiregistration.k8s.io/v1",
        "version": "v1"
      }
    },
    {
      "name": "extensions",
      "versions": [
        {
          "groupVersion": "extensions/v1beta1",
          "version": "v1beta1"
        }
      ],
      "preferredVersion": {
        "groupVersion": "extensions/v1beta1",
      }
    },
... output omitted ...
```

Note that even if the API server is exposed over HTTPS, we were able to bypass the server certificate verification (i.e with the `curl` -k flag).

So, if you need to get more information about the set of endpoints that a specific group includes, you can issue the same previous `curl` command with the appropriate URL path. For instance, to see what the `v1beta1` version of the `extensions` group contains:

```shell
user@k8s-master$ curl https://127.0.0.1:6443/apis/extensions/v1beta1 -k
{
  "kind": "APIResourceList",
  "groupVersion": "extensions/v1beta1",
  "resources": [
    {
      "name": "daemonsets",
      "singularName": "",
      "namespaced": true,
      "kind": "DaemonSet",
      "verbs": [
        "create",
        "delete",
        "deletecollection",
        "get",
        "list",
        "patch",
        "update",
        "watch"
      ],
      "shortNames": [
        "ds"
      ]
    },
... output omitted ...
    {
      "name": "deployments",
      "singularName": "",
      "namespaced": true,
      "kind": "Deployment",
      "verbs": [
        "create",
        "delete",
        "deletecollection",
        "get",
        "list",
        "patch",
        "update",
        "watch"
      ],
      "shortNames": [
        "deploy"
      ]
    },
... output omitted ...
```

This is currently one of the most important and used groups of the API. Here you can see resources endpoints like DaemonSet , Deployment, Ingress, ReplicaSet, and so on. Navigate through the different groups and resources, check their names, the associated actions, short names, and other information as you like.



### Kubectl Verbose Mode

`kubectl` provides a *verbose* mode with different levels that allow us to understand what it is doing on our behalf and show us more detailed output which can be useful in case of debugging. This means that we can use this mode to get information about the HTTP REST requests that `kubectl` sends to get and update cluster resources.

Here is a screenshot from the [kubectl cheat sheet](https://kubernetes.io/docs/reference/kubectl/cheatsheet/#kubectl-output-verbosity-and-debugging) that explains those levels. The needed verbosity level can be passed on the command's argument `--v`.

![kubectl verbose levels](/img/kubectl-verbose.png)

 Let's try to use this mode with level 8 while requesting the list of services in the default namespace. The output below is formatted for readability, expect some more text on your terminal.

```shell
# Get a list of services in the default namespace
user@k8s-master$ kubectl --v=8 get svc
... output omitted ...
GET https://127.0.0.1:6443/api/v1/namespaces/default/services?limit=500
... output omitted ...
Response Status: 200 OK in 29 milliseconds
... output omitted ...
Response Body: {"kind":"ServiceList","apiVersion":"v1","metadata":{"selfLink":"/api/v1/namespaces/default/services","resourceVersion":"22058"},"items":[{"metadata":{"name":"kubernetes","namespace":"default","selfLink":"/api/v1/namespaces/default/services/kubernetes","uid":"81e11bfb-9c39-11e9-8ede-42010a9a0046","resourceVersion":"33","creationTimestamp":"2019-07-01T19:50:41Z","labels":{"component":"apiserver","provider":"kubernetes"}},"spec":{"ports":[{"name":"https","protocol":"TCP","port":443,"targetPort":443}],"clusterIP":"10.55.240.1","type":"ClusterIP","sessionAffinity":"None"},"status":{"loadBalancer":{}}}]}
... output omitted ...
NAME         TYPE        CLUSTER-IP    EXTERNAL-IP   PORT(S)   AGE
kubernetes   ClusterIP   10.55.240.1   <none>        443/TCP   2h

# Get a list of services in the kube-system namespace
user@k8s-master$ kubectl --v=8 get svc -n kube-system
GET https://127.0.0.1:6443/api/v1/namespaces/kube-system/services?limit=500
... output omitted ...
Response Status: 200 OK in 162 milliseconds
... output omitted ...
Response Body: {"kind":"ServiceList","apiVersion":"v1","metadata":{"selfLink":"/api/v1/namespaces/kube-system/services","resourceVersion":"22395"},"items":[{"metadata":{"name":"default-http-backend","namespace":"kube-system","selfLink":"/api/v1/namespaces/kube-system/services/default-http-backend","uid":"a7441324-9c39-11e9-b164-42010a9a0046","resourceVersion":"326","creationTimestamp":"2019-07-01T19:51:44Z","labels":{"addonmanager.kubernetes.io/mode":"Reconcile","k8s-app":"glbc","kubernetes.io/cluster-service":"true","kubernetes.io/name":"GLBCDefaultBackend"},"annotations":{"kubectl.kubernetes.io/last-applied-configuration":"{\"apiVersion\":\"v1\",\"kind\":\"Service\",\"metadata\":{\"annotations\":{},\"labels\":{\"addonmanager.kubernetes.io/mode\":\"Reconcile\",\"k8s-app\":\"glbc\",\"kubernetes.io/cluster-service\":\"true\",\"kubernetes.io/name\":\"GLBCDefaultBackend\"},\"name\":\"default-http-backend\",\"namespace\":\"kube-system\"},\"spec\":{\"ports\":[{\"name\":\"http\",\"port\":80,\"protocol\":\"TCP\",\"targetPort\":808 [truncated 2409 chars]
... output omitted ...
NAME                   TYPE        CLUSTER-IP     EXTERNAL-IP   PORT(S)        AGE
default-http-backend   NodePort    10.55.240.10   <none>        80:30077/TCP   2h
heapster               ClusterIP   10.55.248.97   <none>        80/TCP         2h
metrics-server         ClusterIP   10.55.249.81   <none>        443/TCP        2h
```

Verbosity level 8 shows us the HTTP request like GET requests and the URL of the API which includes the group, version, and targeted resource. It also shows the response status and body. If the response body is so long like in the case of the second command above, the response body will be truncated.

In contrast, the verbosity level 9 shown next allows us to see not only the HTTP request, but also the `curl` command `kubectl` used to send the request. Moreover, the response body would not be truncated at this level.

```shell
user@k8s-master$ kubectl --v=9 get pods
... output omitted ...
curl -k -v -XGET  -H "Accept: application/json" -H "User-Agent: kubectl/v1.10.4 (linux/amd64) kubernetes/5ca598b" https://127.0.0.1:6443/api/v1/namespaces/default/pods?limit=500

GET https://127.0.0.1:6443/api/v1/namespaces/default/pods?limit=500 200 OK in 257 milliseconds

... output omitted ...
Response Body: {"kind":"PodList","apiVersion":"v1","metadata":{"selfLink":"/api/v1/namespaces/default/pods","resourceVersion":"14451"},"items":[]}
No resources found.

user@k8s-master$ kubectl --v=9 get svc
... output omitted ...
curl -k -v -XGET  -H "Accept: application/json" -H "User-Agent: kubectl/v1.10.4 (linux/amd64) kubernetes/5ca598b" https://127.0.0.1:6443/api/v1/namespaces/default/services?limit=500

GET https://127.0.0.1:6443/api/v1/namespaces/default/services?limit=500 200 OK in 88 milliseconds

... output omitted ...
Response Body: {"kind":"ServiceList","apiVersion":"v1","metadata":{"selfLink":"/api/v1/namespaces/default/services","resourceVersion":"16103"},"items":[{"metadata":{"name":"kubernetes","namespace":"default","selfLink":"/api/v1/namespaces/default/services/kubernetes","uid":"81e11bfb-9c39-11e9-8ede-42010a9a0046","resourceVersion":"33","creationTimestamp":"2019-07-01T19:50:41Z","labels":{"component":"apiserver","provider":"kubernetes"}},"spec":{"ports":[{"name":"https","protocol":"TCP","port":443,"targetPort":443}],"clusterIP":"10.55.240.1","type":"ClusterIP","sessionAffinity":"None"},"status":{"loadBalancer":{}}}]}
... output omitted ...
NAME         TYPE        CLUSTER-IP    EXTERNAL-IP   PORT(S)   AGE
kubernetes   ClusterIP   10.55.240.1   <none>        443/TCP   1h
```

You can also take a moment to check the URLs of the GET requests and see if you can extract the API group and `apiVersion`.  It is also worth noting that the curl commands `kubectl` uses specifies in their header that they only accept JSON format. This JSON formatted reponse body is then processed by kubectl and printed to you in a pretty format.

### Kubectl is Just Easier

 At this point, you know where to find the underlying `curl` command used by `kubectl` and the HTTP REST requests it sends to the k8s RESTful API. You can use this information to do the same job as `kubectl` with other client (e.g. Postman). Basically, with `curl` you can use any of the [HTTP verbs](https://tools.ietf.org/html/rfc7231#section-4) to manage resources. Also, you now know how to navigate the API groups. Some resources support additional verbs provided by k8s as you can see if you look back at the second listing in the *API Groups* section and spot the following lines:

```json
"verbs": [
        "create",
        "delete",
        "deletecollection",
        "get",
        "list",
        "patch",
        "update",
        "watch"
      ]
```



So, `kubectl` is an easy and convenient tool that facilitate our tasks, but nothing should prevent you from using `curl` to create, get, or update k8s objects and resources directly. Oh, maybe one thing could stop you: AUTHENTICATION.

For a cluster that uses X509 client certs (which is the case of minikube used in the following examples), you can find the keys and certs files using `kubectl config view`, as I showed in the previous post. Then, you can  pass those certs as arguments to the `curl` commands in order to authenticate your requests with the k8s API server. For example, if you have a pod called busybox and you want to get the logs of this pod, the equivalent of `kubectl logs busybox` is (supposing that your files are in /tmp) :

```shell
user@k8s-master$ curl --cert /tmp/client.pem --key /tmp/client-key.pem \
--cacert /tmp/ca.pem -v -XGET https://127.0.0.1:6443/api/v1/namespaces/default/pods/busybox/log
```

Some examples of other calls you can make:

```shell
GET /api/v1/namespaces/{namespace}/pods/{name}/exec
GET /api/v1/namespaces/{namespace}/pods/{name}/log
GET /api/v1/watch/namespaces/{namespace}/pods/{name}
```

You may be thinking that getting resources is easy, but creating resources is also possible. Let's try to create a busybox pod, starting by creating a file named `busypod.json` with the following content:

```json
{
   "kind":"Pod",
   "apiVersion":"v1",
   "metadata":{
      "name":"busypod",
      "namespace":"default",
      "labels":{
         "name":"examplepod"
      }
   },
   "spec":{
      "containers":[
         {
            "name":"busybox",
            "image":"busybox",
            "command":["sleep", "3600"]
         }
      ]
   }
}
```

This file is the equivalent of a YAML file. We did it in JSON because it is easier when working with `curl`. In fact, as we saw earlier,  `kubectl`  translates the YAML files into JSON format when calling the API server. Then, enter the following curl command. Notice that we are using a POST HTTP method and not GET.

```shell
$ curl --cert <path_to>/client.crt --key <path_to>/client.key --cacert <path_to>/ca.crt https://192.168.99.100:6443/api/v1/namespaces/default/pods -XPOST -H'Content-Type: application/json' -d@busypod.json
{
  "kind": "Pod",
  "apiVersion": "v1",
  "metadata": {
    "name": "busypod",
    "namespace": "default",
    "selfLink": "/api/v1/namespaces/default/pods/busypod",
    "uid": "a7ab3c0e-9d08-11e9-8f57-0800275e9471",
    "resourceVersion": "99053",
    "creationTimestamp": "2019-07-02T20:33:30Z",
    "labels": {
      "name": "examplepod"
    }
  },
  "spec": {
    "volumes": [
      {
        "name": "default-token-njddp",
        "secret": {
          "secretName": "default-token-njddp",
          "defaultMode": 420
        }
      }
    ],
    "containers": [
      {
        "name": "busybox",
        "image": "busybox",
        "command": [
          "sleep",
          "3600"
        ],
        "resources": {

        },
        "volumeMounts": [
          {
            "name": "default-token-njddp",
            "readOnly": true,
            "mountPath": "/var/run/secrets/kubernetes.io/serviceaccount"
          }
        ],
        "terminationMessagePath": "/dev/termination-log",
        "terminationMessagePolicy": "File",
        "imagePullPolicy": "Always"
      }
    ],
    "restartPolicy": "Always",
    "terminationGracePeriodSeconds": 30,
    "dnsPolicy": "ClusterFirst",
    "serviceAccountName": "default",
    "serviceAccount": "default",
    "securityContext": {

    },
    "schedulerName": "default-scheduler",
    "tolerations": [
      {
        "key": "node.kubernetes.io/not-ready",
        "operator": "Exists",
        "effect": "NoExecute",
        "tolerationSeconds": 300
      },
      {
        "key": "node.kubernetes.io/unreachable",
        "operator": "Exists",
        "effect": "NoExecute",
        "tolerationSeconds": 300
      }
    ],
    "priority": 0,
    "enableServiceLinks": true
  },
  "status": {
    "phase": "Pending",
    "qosClass": "BestEffort"
  }
}
```

Check if the pod has been created:

```shell
$ kubectl get pods
NAME         READY     STATUS    RESTARTS   AGE
busypod      1/1       Running   0          31s
```

If you are using a managed Kubernetes cluster from a public cloud provider, the authentication method may be different. The commands then need to be adapted accordingly.

### Summary

This post demystified the Kubernetes API and showed how you can manage Kubernetes cluster resources with a client different than kubectl.

### Additional Resources

[https://medium.com/@nieldw/curling-the-kubernetes-api-server-d7675cfc398c](https://medium.com/@nieldw/curling-the-kubernetes-api-server-d7675cfc398c)

*[k8s]: Kubernetes
