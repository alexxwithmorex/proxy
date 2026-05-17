import socket
import signal
import threading
import select
import time


blacklist = {"x.com", "chatgpt.com", "example.com"}
blacklist_lock = threading.Lock()   #adding a lock so that only one thread at the time can access the blacklist

def blacklist_management():
    print("commands : block <hostname>  |  unblock <hostname>  |  ls")
    while True:
        string = input(">> ")
        cmd = string.split()

        if cmd[0] == "ls":
            #print("Acquiring lock ...")
            with blacklist_lock:
                print(f"blacklist : {blacklist}")

        elif cmd[0] == "block":
            name = cmd[1] 
            with blacklist_lock:
                blacklist.add(name)
            print(f"blocked : {name}")

        elif cmd[0] == "unblock":
            name = cmd[1]
            with blacklist_lock:
                blacklist.remove(name)
            print(f"unblocked : {name}")

        else :
            print("command doesn't exist")



def handle_http(client, request):
    
    first_line = request.decode(errors='ignore').split('\n')[0]
    url = first_line.split(' ')[1]

    #remove http:// and final / to get the hostname only
    if '://' in url:
        url = url.split('://')[1]
    slash_pos = url.find('/')
    if slash_pos == -1:
        host = url
    else:
        host = url[:slash_pos]
        
    if host in blacklist :
        client.send(b'HTTP/1.1 403 Forbidden \r\n\r\n<h1>I\'m a teapot and you can\'t access that website </h1>')
        time.sleep(0.5)
        client.close()
        return

    port = 80
    print(f"Connecting to: {host}:{port}")

    try:

        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.connect((host, port)) #host being what we just stripped from request
        server_socket.sendall(request)

        server_socket.settimeout(2)  #coz it was too slow

        #talk back to browser via client socket
        try :
            while True:
                data = server_socket.recv(4096)
                if not data:
                    break
                client.send(data)
        except socket.timeout :
            pass

    except Exception as e:
        print(f"HTTP Error: {e}")

    finally :
        server_socket.close()
        client.close()


def handle_https(client, host, port):

    if host in blacklist:
        client.send(b'HTTP/1.1 200 \r\n\r\n')
        client.close()
        return

    try :
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.connect((host,port))
        client.send(b'HTTP/1.1 200 \r\n\r\n') #tell browser that connection works

        while True:
            #watch both sockets and only keep the readable from (read,write,err) data
            readable, _, _ = select.select([client, server_socket], [], [], 5)
            
            if not readable:
                #5sec passed & no data on either socket
                break
            
            for sock in readable:
                data = sock.recv(4096)
                
                if not data:
                    return
                
                #send to other socket
                if sock is client:
                    server_socket.send(data)   #sock A -> sock B
                else:
                    client.send(data)          #sock A <- sock B

        server_socket.close()

    except Exception as e:
        print(f"HTTP Error: {e}")

    finally :
        client.close()



def handle_request(client):
    request = client.recv(4096)
    if not request:
        client.close()
        return

    #print & decode full request
    print("\n--- Incoming Request ---")
    print(request.decode(errors='ignore'))

    #on line 1, extract the 1st word get/connect
    fst_line = request.decode(errors='ignore').split('\n')[0]
    rq_type = fst_line.split(' ')[0]

    if rq_type == 'CONNECT':
        #CONNECT www.blablabla.com:443 HTTP/1.1
        hosteport = fst_line.split(' ')[1]    #remove "connect" & "http1.1"
        host = hosteport.split(':')[0]          #remove 443
        port = int(hosteport.split(':')[1])     #443
        handle_https(client, host, port)
    elif rq_type == 'GET':
        #GET http://blabla.com/ HTTP/1.1
        handle_http(client, request)
    else :
        client.close()
        return




#main
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) #to avoid port being put on hold
s.bind(('127.0.0.1', 8080))
s.listen(5)
print("Proxy listening on port 8080...")

blacklist_thread = threading.Thread(target=blacklist_management)
blacklist_thread.daemon = True
blacklist_thread.start()

while True:
    client, addr = s.accept()
    print(f"Connection from {addr}")
    #start new thread for the request that was just accepted
    t = threading.Thread(target=handle_request, args=(client,))
    t.daemon = True #thread dies if program stops
    t.start()
