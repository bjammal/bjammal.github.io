---
layout: post
title: Site-to-Site VPN on a Single Host Using OpenVPN
---

This post aims at providing a step-by-step configuration guide for setting up a Site-to-Site VPN using the opensource OpenVPN. It is based on this [howto](https://openvpn.net/index.php/open-source/documentation/howto.html) guide of the tool’s website. Basically, you may not need to read this post if you follow the steps in the howto. But this is intended to give more detailed instructions illustrated with an example, and to show one way to test a configuration before throwing the commands into a production environment.

First things first, we need two machines to act as client and server. In our example, we will use two VMs running on the same physical host and connected through a host-only network. You can launch these two VMs manually or using [Vagrant](https://www.vagrantup.com/). In Fig 1. these two VMs are referred to as node1 and node2. The figure also shows the subnetting used in our example.

![img](https://cdn-images-1.medium.com/max/800/1*R0Nzu7JHWj54V3antbkYOA.png)Fig 1. Topology

### Install OpenVPN

Once you have the two VMs up and running, it’s time to install and configure OpenVPN. On ubuntu-based OS, *OpenVPN* can be easily installed using the package manager. Other options are also available, please check the howto page for more info. Run the following commands inside the VMs.

```
sudo apt-get install openvpn
sudo apt-get install easy-rsa
```

*easy-rsa* is a Public Key Infrastructure (PKI) management tool, that can be used to generate a certificate and a public-private key pair (If you don’t have them) that are going to be used to authenticate when establishing the VPN tunnel. We will start with the configuration of the server and next we detail the client’s configuration.

### Server Configuration

#### 1. Generate the master Certificate Authority (CA) certificate & key

First, we need to setup the key pair and a certificate authority that we will use to sign the client and server’s certificate.

> If you are using Linux, BSD, or a unix-like OS, open a shell and cd to the **easy-rsa** subdirectory. If you installed OpenVPN from an RPM or DEB file, the easy-rsa directory can usually be found in **/usr/share/doc/packages/openvpn** or **/usr/share/doc/openvpn** (it’s best to copy this directory to another location such as **/etc/openvpn**, before any edits, so that future OpenVPN package upgrades won’t overwrite your modifications). If you installed from a .tar.gz file, the easy-rsa directory will be in the top level directory of the expanded source tree.

So copy the directory as recommended:

```
cp -R /usr/share/doc/openvpn /etc/openvpn
cd /etc/openvpn/easy-rsa
```

Now edit the **vars** file and set the KEY_COUNTRY, KEY_PROVINCE, KEY_CITY, KEY_ORG, and KEY_EMAIL parameters. Don’t leave any of these parameters blank. Then initialize the PKI:

```
. ./vars
./clean-all
./build-ca
```

This will create a sub-directory called *keys* with the following files:

```
$ sudo ls -l /etc/openvpn/easy-rsa/keys/
total 52
-rw-r--r-- 1 root root 5679 Apr 27 08:29 01.pem
-rw-r--r-- 1 root root 1777 Apr 27 08:28 ca.crt
-rw------- 1 root root 1708 Apr 27 08:28 ca.key
-rw-r--r-- 1 root root  149 Apr 27 08:29 index.txt
```

#### 2. Generate certificate & key for server

To generate a certificate and a private key for the server, run the following command:

```
./build-key-server server
```

> As in the previous step, most parameters can be defaulted. When the **Common Name** is queried, enter “server”. Two other queries require positive responses, “Sign the certificate? [y/n]” and “1 out of 1 certificate requests certified, commit? [y/n]”.

the *server* argument passed as parameter to the script can be changed. Choose the name that you like.

#### 3. Generate Diffie-Helman Parameters

```
./build-dh
```

This step takes some more time, and when finished, you will have a new file called *dh2048.pem* (could be also dh1024.pem depending on the key length) in the *keys* subdirectory.

#### 4. Create/Edit OpenVPN Server Configuration File

*OpenVPN* provides sample configuration files that we only need to uncomment and/or edit some lines according to our needs.

> the **sample-config-files** directory in **/usr/share/doc/packages/openvpn** or **/usr/share/doc/openvpn** if you installed from an RPM or DEB package.

It’s also recommended to copy these files into another directory so your changes do not overwrite the provided samples. I chose to copy them to the same directory as easy-rsa, /etc/openvpn:

```
cp -R /usr/share/doc/openvpn/sample-config-files/ /etc/openvpn
cd /etc/openvpn/sample-config-files
```

The first thing to do is to point to the location of the certificates and keys generated in steps 1 and 2. In my example, I kept the files in easy-rsa subdirectory **/etc/openvpn/easy-rsa/keys.** Edit this value if you chose a different location.

```
# SSL/TLS root certificate (ca), certificate
# (cert), and private key (key).  Each client
# and the server must have their own cert and
# key file.  The server and all clients will
# use the same ca file.
#
# See the "easy-rsa" directory for a series
# of scripts for generating RSA certificates
# and private keys.  Remember to use
# a unique Common Name for the server
# and each of the client certificates.
#
# Any X509 key management system can be used.
# OpenVPN can also use a PKCS #12 formatted key file
# (see "pkcs12" directive in man page).
ca /etc/openvpn/easy-rsa/keys/ca.crt
cert /etc/openvpn/easy-rsa/keys/server.crt
key /etc/openvpn/easy-rsa/keys/server.key  # This file should be kept secret
# Diffie hellman parameters.
# Generate your own with:
#   openssl dhparam -out dh1024.pem 1024
# Substitute 2048 for 1024 if you are using
# 2048 bit keys.
dh /etc/openvpn/easy-rsa/keys/dh2048.pem
```

This is all we need on the server side if we only want the client machine to securely communicate with the server machine. My preferred way to roll out a setup is to divide it into sub-tasks and do it incrementally. So We will come back to the server to continue the site-to-site configuration once we make sure that the client is able to establish a basic connection to the server.

### Client Configuration

#### 1. Generate the client’s certificate & keys

Similarly to the server, copy the easy-rsa directory to start generating the keys.

```
cp -R /usr/share/doc/openvpn /etc/openvpn
cd /etc/openvpn/easy-rsa
. ./vars
./clean-all
```

Instead of generating a new CA certificate, we can copy the files from the server and place them in the /keys sub-directory of the client (use any transfer method you prefer, over network, or using a usb key). Now, we have the CA in place in order to sign the client’s certificate that we will create next. Note that the client also checks if the server’s certificate and keys are signed by the CA. In order to generate the client’s certificate, issue the following command:

```
./build-key client
```

Again, *client* is the value that we have chosen for the client’s certificate **common name,** you are free to pass the value you want to the script.

#### 2. Create/Edit OpenVPN Client Configuration File

The client needs to know the IP, or the name if you have a DNS service, of the server as well as the port on which the server is listening. The port can be left to the default value. Also, we will specify the location of the certificates and keys.

```
# The hostname/IP and port of the server.
# You can have multiple remote entries
# to load balance between the servers.
remote 192.168.100.200 1194
# SSL/TLS parms.
# See the server config file for more
# description.  It's best to use
# a separate .crt/.key file pair
# for each client.  A single ca
# file can be used for all clients.
ca /etc/openvpn/easy-rsa/keys/ca.crt
cert /etc/openvpn/easy-rsa/keys/client.crt
key /etc/openvpn/easy-rsa/keys/client.key
```

And this is all we have to do for the client. Let’s test the connectivity.

Start the server:

```
openvpn [server config file]
```

If you are not in the directory where the server config file is placed, you need to use the relative or absolute path to the file’s name.

Start the client:

```
openvpn [client config file]
```

Now, the standard output on the terminal running the server should give you an indication whether the client were able to build the tunnel successfully (see Fig 2 below), but you can try to reach the tunnel end on the server by issuing a ping from the client:

![img](https://cdn-images-1.medium.com/max/800/1*gipm9ssSXcFPyZ_xFdHysw.png)Fig 2. Client-Server connection establishment

```
$ ping 10.8.0.1
PING 10.8.0.1 (10.8.0.1) 56(84) bytes of data.
64 bytes from 10.8.0.1: icmp_seq=1 ttl=64 time=1.49 ms
64 bytes from 10.8.0.1: icmp_seq=2 ttl=64 time=0.468 ms
64 bytes from 10.8.0.1: icmp_seq=3 ttl=64 time=0.418 ms
^C
--- 10.8.0.1 ping statistics ---
3 packets transmitted, 3 received, 0% packet loss, time 2000ms
```

If the ping is successful, then the VPN communication is successfully established between the client machine and the server machine.

### Site-to-Site Configuration

In the howto guide, they don’t call it site-to-site configuration, instead they call it expansion of the VPN to include subnets on either the client or the server side. They are right! because with OpenVPN, you can do a unidirectional distribution to only include subnets on one side of the connection e.g. only send the server’s subnet to the client, without giving the server the ability to reach subnets behind the client machine. This section corresponds to this [scope](https://openvpn.net/index.php/open-source/documentation/howto.html#scope) section of the howto guide.

#### Create virtual interfaces

To simulate a LAN behind each end of the VPN tunnel, we will create a virtual interface *eth1:0* on both the client and the server nodes.

To can be done as easily as issuing the following command:

```
ifconfig eth0:0 ip-address/prefix-length up
```

For our example illustrated in Fig 1, we will run these commands:

```
[Node1] ifconfig eth1:0 192.168.200.200/24 up
[Node2] ifconfig eth1:0 192.168.40.129/29 up
```

#### Advertise Server’s LAN to the client

Advertising the LAN behind the vpn server is straightforward. Just add this line to the server config file on the server.

```
push "route 192.168.200.0 255.255.255.0"
```

Now the client should be able to ping the LAN interface *eth1:0.*

#### Advertise Client’s LAN to the server

Advertising the client’s LAN subnet to the server takes more step, but it is still quite easy, and it is done in two parts:

In the first part, on the server node, we will create a sub-directory called *ccd*, which stands for *client config directory* in OpenVPN vocabulary. You can choose another name. then, create a file with the same name as the **common name** of the client certificate and add the *iroute* directive for the client’s subnet. The following commands summarize this part.

```
cd /etc/openvpn
mkdir ccd
cd ccd
touch client
echo “iroute 192.168.40.128 255.255.255.248” > client
```

The second part consists of changes that have to be made in the server config file. Add the following lines to the file:

```
client-config-dir ccd
route 192.168.40.128 255.255.255.248
```

Congratulations! we have a LAN to LAN secure communication over VPN. You can source a ping from any of the *eth1:0* to the other one.
