---
layout: post
tags: kubernetes authentication
title: "Kubernetes Cluster Access: Authenticate and Authorize an External User"
---

## Overview

Creating a Kubernetes cluster on baremetal (e.g. using tools like kubeadm) consists of an initialization command followed by creating some directories and copying some files. When successfully completed, your CLI client *kubectl* used to interact with the cluster is auto-magically configured and ready to connect to the cluster. If you use managed clusters on public cloud, configuring *kubectl* is usually a one command. Behind the scenes of this configuration a lot of work is done.  
`kubectl` is a CLI client that can be used to manage multiple k8s clusters. Commands are sent as API requests to the cluster API server, which authenticates and authorizes them before passing them to the controller responsible of handling the kind of received request.   

In this post, we will explore the details of how `kubectl` commands are authenticated. We will also create a new external user and authorize its access to the cluster using RBAC. The commands output is based on a minikube  installation. The values in your output will be slightly different if you are using a baremetal or a managed k8s cluster.

---

`Kubectl` is configured using a configuration file, known as *kubeconfig*, which contains an element called context \[1][2]. The *context* is defined by three parameters:

- **cluster name** of the cluster to be used
- **namespace (optional)** can be used to limit the cluster's access to a particular namespace
- **user** on behalf of whom k8s resources and objects are manipulated

When the cluster's API server receives a request, the request's user - defined in the context - gets authenticated. Then, the authorization process checks if the user  has the permission to carry the requested operation.

> Users in Kubernetes can be of two types: end or normal users managed outside Kubernetes (we will call them external), and service account users managed by Kubernetes API [3].

Clusters initialization scripts like `kubeadm` write (or instruct you to place) the kubeconfig file in a subdirectory (more precisely  `.kube` directory) of the home directory of the logged in user on the master node where the script was launched. By default, `kubectl` looks for its config file in this specific subdirectory of the logged user. Therefore, the config file must be copied to the home directory of each user who needs to access the cluster. Those scripts also define a default user to access the cluster.  

> Do not confuse the user that k8s authenticates and is defined in the context with the user used by kubectl to locate kubeconfig. They may or may not be the same.


The following commands can be used to get information about  the contexts and users. The default user here is called *minikube*.
```shell
# To check the current context
$ kubectl config current-context
minikube

# To list contexts, the * indicates the current context
$ kubectl config get-contexts
CURRENT   NAME            CLUSTER    AUTHINFO   NAMESPACE
*         minikube        minikube   minikube   

# To see the context details: user, cluster, namespace
$ kubectl config view --output=jsonpath='{.contexts[?(@.name=="minikube")]}'
map[context:map[cluster:minikube user:minikube] name:minikube]

# To view the entire default config, explained in more details later
$ kubectl config view
apiVersion: v1
clusters:
- cluster:
    certificate-authority: $HOME/.minikube/ca.crt
    server: https://192.168.99.100:8443
  name: minikube
contexts:
- context:
    cluster: minikube
    user: minikube
  name: minikube
current-context: minikube
kind: Config
preferences: {}
users:
- name: minikube   # default user
  user:
    client-certificate: $HOME/.minikube/client.crt
    client-key: $HOME/.minikube/client.key
```
## Configuring Access of a New User
Imagine that we have a database administrator who needs to manage databases instances on a k8s cluster.  However, we do not want him to see what other people / roles are doing on the cluster. For this, we will create a new namespace and call it `databases`. We will then create a new external (normal) user, call him `DbUser`, and allow him to access only the `databases` namespace.

Assuming that the namespace exists or has been created, the process consists of the following steps:

1. Create a user (or use an existing one).
2. Generate public/private keypair and certificates.
3. Update the kubeconfig file to reference the newly keypair and certificates.
4. Define a new context referencing the user, namespace and targeted cluster.  
   After this step, *kubeconfig* is properly configured to give kubectl the appropriate information it needs to use in the the API requests. But the cluster has no information about the created user and is not yet able to authorize its requests. In other words, we have solved the authentication, but we still need to solve the authorization. This is why we still need to:
5. Create RBAC Role and RoleBinding to define the user's permissions.

#### Step 1: Create a User

```shell
# Create a new user
$ sudo useradd -s /bin/bash DbUser

# Set the password
$ sudo passwd DbUser
Enter new UNIX password:
Retype new UNIX password:
passwd: password updated successfully
```

#### Step 2: Generate user's keys and certificates

```shell
# Create a private key
$ openssl genrsa -out DbUser.key 2048
Generating RSA private key, 2048 bit long modulus
......+++
.........+++
e is 65537 (0x10001)

# Generate a Certificate Signing Request (CSR) using the created key
$ openssl req -new -key DbUser.key \
-out DbUser.csr -subj "/CN=DbUser"

# Generate a self-signed certificate using the CSR
$ sudo openssl x509 -req -in DbUser.csr \
-CA /etc/kubernetes/pki/ca.crt \
-CAkey /etc/kubernetes/pki/ca.key \
-CAcreateserial \
-out DbUser.crt -days 45

Signature ok
subject=/CN=DbUser
Getting CA Private Key
```

If you look back at the default config file, the keys and certs of the default user (minikube) are placed in the `~/.minikube` subdirectory. It may be a good idea to copy the new files of DbUser (DbUser.key and DbUser.crt) in the same directory.

#### Step 3 and 4: Update the kubeconfig file

Before doing any modifications, it is useful to review the default configuration with `kubectl config view`. The output looks like:

```shell
apiVersion: v1
clusters:
- cluster:
    certificate-authority: $HOME/.minikube/ca.crt
    server: https://192.168.99.100:8443
  name: minikube    # name of the cluster
contexts:
- context: 			# default context defined by minikube
    cluster: minikube
    user: minikube
  name: minikube
current-context: minikube
kind: Config
preferences: {}
users:
- name: minikube
  user:  			# user credentials
    client-certificate: $HOME/.minikube/client.crt
    client-key: $HOME/.minikube/client.key
```

This command is the equivalent of displaying the kubeconfig file with `cat ~/.kube/config`. The above output is from a minikube installation. If you are using any other type of installation the output must be similar with different values. `$HOME` will be replaced with the absolute path to your home directory.  
Note the name of the cluster for later use, that is `minikube` in our case (see the line with a comment). You can also copy/backup this file if you want to refer to in later.  
To add the user credentials and define a new context, enter the following commands.

```shell
# Check the different options of kubectl config set-credentials
# by adding the flag -h.
# Place the certs and keys in a safe directory and use the path
# to replace "path_to".
# Add the user and credentials to the kubeconfig file
$ kubectl config set-credentials DbUser \
--client-certificate=/path_to/DbUser.crt \
--client-key=/path_to/DbUser.key

# add a new context for the new user in kubeconfig
$ kubectl config set-context DB-context \
--cluster=minikube \
--namespace=databases \
--user=DbUser
Context "DB-context" created.
```

`--cluster=minikube` sets the name of the targeted cluster to *minikube* and `--namespace=databases` sets *databases* as the namespace of this context, where the user is granted access. You can omit the namespace argument if you want to define a cluster-wide access.

To verify the modifications you can use the following commands:

```shell
# list available contexts
$ kubectl config get-contexts
CURRENT   NAME            CLUSTER    AUTHINFO   NAMESPACE
          DB-context      minikube   DbUser     databases
*         minikube        minikube   minikube   


# try to use the new context to access cluster resources. You should not be allowed.
$ kubectl --context=DB-context get pods
Error from server (Forbidden): pods is forbidden: User "DbUser"
cannot list pods in the namespace "databases"
```

We will fix the 'forbidden' error in step 5.

This is how the kubeconfig file looks after adding the new context and user credentials (you can compare it with the original one):
```shell
apiVersion: v1
clusters:
- cluster:
    certificate-authority: $HOME/.minikube/ca.crt
    server: https://192.168.99.100:8443
  name: minikube
contexts:
- context:
    cluster: minikube
    namespace: databases
    user: DbUser
  name: DB-context
- context:
    cluster: minikube
    user: minikube
  name: minikube
current-context: minikube
kind: Config
preferences: {}
users:
- name: DbUser
  user:
    client-certificate: $HOME/.minikube/DbUser.crt
    client-key: $HOME/.minikube/DbUser.key
- name: minikube
  user:
    client-certificate: $HOME/.minikube/client.crt
    client-key: $HOME/.minikube/client.key
```
#### Step 5: Create RBAC objects

First, we will create a role called *dbuser* in the *databases* namespace we defined earlier in the context. We will assign full capabilities (all operations) on *deployments*, *replicasets*, and *pods*. Create a file in your working directory with the following content. Let's say I named this file *dbrole.yaml*.

```yaml
kind: Role
apiVersion: rbac.authorization.k8s.io/v1beta1
metadata:
  namespace: databases  # Same namespace as the one in the context
  name: dbuser
rules:
- apiGroups: ["", "extensions", "apps"]
  resources: ["deployments", "replicasets", "pods"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"] # You can also use ["*"]
```

Create the role with `kubectl apply -f dbrole.yaml`.

Next, we need to create a role binding to assign our user to the role we just created. Create a file *dbrole-binding.yaml* with the following content:

```yaml
kind: RoleBinding
apiVersion: rbac.authorization.k8s.io/v1beta1
metadata:
  name: dbuser-role-binding
  namespace: databases
subjects:
- kind: User      # Here we say it's a normal user and not a service account
  name: DbUser  # Here is where we define the user we created and defined in the context
  apiGroup: ""
roleRef:
  kind: Role
  name: dbuser
  apiGroup: ""
```

Create the role binding with `kubectl apply -f dbrole-binding.yaml`.

Now if you test again with `kubectl --context=DB-context get pods`, you should not be denied from viewing pods for example. However, you may get `no resources found` if nothing is running on the cluster. Try to create pods or deployments in the databases namespace and list them.

```shell
# Create a deployment of mongoDB
$ kubectl run mongo --image=mongo --context=DB-context -n databases
deployment.apps/mongo created

# List all deployments in the namespace
$ kubectl get deployments --context=DB-context -n databases
NAME    READY   UP-TO-DATE   AVAILABLE   AGE
mongo   1/1     1            1           108s

# List all pods in the namespace
$ kubectl get pods --context=DB-context -n databases
NAME                     READY   STATUS    RESTARTS   AGE
mongo-845fdc5c7b-2x7zz   1/1     Running   0          2m37s
```
We have successfully configured an additional external user to access a Kubernetes cluster. Setting a context and a user in kubeconfig allows the user to get authenticated but does not give the user any permission on the cluster. An additional step of creating RBAC objects (role and role binding) was required to assign the appropriate permissions. For the curious, you can play around with the verbs of the role, add more namespaces, etc.

### References  

[1] [https://kubernetes.io/docs/concepts/configuration/organize-cluster-access-kubeconfig/#context](https://kubernetes.io/docs/concepts/configuration/organize-cluster-access-kubeconfig/#context)  
[2] [https://kubernetes.io/docs/reference/kubectl/cheatsheet/#kubectl-context-and-configuration](https://kubernetes.io/docs/reference/kubectl/cheatsheet/#kubectl-context-and-configuration)  
[3] [https://kubernetes.io/docs/reference/access-authn-authz/authentication/#users-in-kubernetes](https://kubernetes.io/docs/reference/access-authn-authz/authentication/#users-in-kubernetes)

*[k8s]: Kubernetes
*[RBAC]: Role-Based Access Control
