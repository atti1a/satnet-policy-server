#include "mission_server.h"
#include <fcntl.h>
#include <stdio.h>
#include <string>
#include <map>


//add ack for cancel demand
enum TR_state {SENT, ACCEPT, REJECT, CANCEL, WITHDRAWL_SENT, WITHDRAWL_ACK};

struct TR
{
    int reqID;
    int gsID;
    time_t start;
    time_t end;
    TR_state state;
};

std::map<int, struct TR> time_requests;


void ack_cb(int reqID, bool accepted)
{
    if(time_requests.count(reqID) == 0){
        printf("Invalid ID\n");
        return;
    }
    struct TR& tr = time_requests[reqID];
    tr.state = (accepted ? ACCEPT : REJECT);
    if(accepted){
        printf("YAY, using time on gs %d from %ld to %ld\n", tr.gsID, tr.start, tr.end);
    }
    else{ 
        printf("NOOOO, can't use time on gs %d from %ld to %ld\n", tr.gsID, tr.start, tr.end);
    }
}

void gs_cb(std::vector<struct GroundStationInfo>& gs_list)
{
    //TO DO
    //Use TLE to propagate forward through time
    //Match with the lat and long of gs in list
    //send time requests
}

void canc_cb(int reqID)
{
    if(time_requests.count(reqID) == 0){
        printf("Invalid ID for cancellation\n");
        return;
    }
    struct TR& tr = time_requests[reqID];
    tr.state = CANCEL; 
    printf("Cancelled time on gs %d from %ld to %ld\n", tr.gsID, tr.start, tr.end);
}

void wd_cb(int reqID, bool accepted)
{
    if(time_requests.count(reqID) == 0){
        printf("Invalid ID\n");
        return;
    }
    //remove the withdrawn time from time_requests
    time_requests.erase(reqID);
    
}

int request_cb(void *arg){
    MissionSocket *ms = (MissionSocket *)arg;
    if(time_requests.size() == 0){
        return EVENT_KEEP;
    }
    ms->send_time_request();
    return EVENT_KEEP;
}

void add_time(MissionSocket& ms, time_t start, time_t end, int gsID)
{
    int id = ms.queue_time_reqest(start, end, gsID);
    struct TR tr = {id, gsID, start, end, SENT};
    time_requests.insert(std::pair<int, struct TR> (id, tr));
}

void withdrawl_time(MissionSocket& ms, int reqID)
{
    ms.queue_withdrawl_request(reqID);
    time_requests[reqID].state = WITHDRAWL_SENT;
}

int bind_to_local_addr(std::string local_addr, int port){
    printf("Binding locally to %s\n", local_addr.c_str());

    int sockfd = socket(AF_INET, SOCK_STREAM, 0);
    if(sockfd == -1){
        printf("Error creating binding socket. Exiting...\n");
        exit(1);
    }

    //TO DO only supports IPv4
    struct sockaddr_in local_sock;
    local_sock.sin_family = AF_INET;
    local_sock.sin_addr.s_addr = inet_addr(local_addr.c_str());
    local_sock.sin_port = port; //bind to any port

    if(bind(sockfd, (sockaddr *)&local_sock, sizeof(local_sock)) == -1){
        perror("Failed to bind");
        exit(1);
    }
    return sockfd;
}


void connect_to_policy_server(int ms_fd, std::string remote_server, int remote_port){
    printf("Connecting to remote mission server at %s:%d\n", remote_server.c_str(), remote_port);

    //TO DO only supports IPv4
    struct sockaddr_in remote_addr;
    remote_addr.sin_family = AF_INET;
    if(inet_aton(remote_server.c_str(), (in_addr *)&remote_addr.sin_addr.s_addr) == 0){
        printf("Invalid remote server IP address: %s", remote_server.c_str());
        exit(1);
    }
    if(remote_port > MAX_PORT){
        printf("Invalid remote server port: %d", remote_port);
        exit(1);
    }
    remote_addr.sin_port = remote_port; //bind to any port
    if(connect(ms_fd, (sockaddr *)&remote_addr, sizeof(remote_addr)) == -1){
        perror("Connect to remote server failed");
        exit(1);
    }
}


int main(int argc, char **argv)
{
    //hack to pass command line testing
    if(argc == 1){
        printf("Not processing the rest of the commandline");
    }
    else if(argc != 5){
        printf("Usage: ms <local-addr> <local-port> <remote-server> <remote-port>\n");
        exit(1);
    }
    else{
        int local_port = atoi(argv[2]);
        std::string local_addr = argv[1];
        //return the fd of the mission socket
        //TO DO get the local interfaces and choose from one of those
        //specify if we are connecting locally or externally
        int ms_fd = bind_to_local_addr(local_addr, local_port);

        std::string remote_server = argv[3];
        int remote_port = atoi(argv[4]);
        connect_to_policy_server(ms_fd, remote_server, remote_port);
    }
    
    //int fd = open("ack_test.json", O_RDWR | O_APPEND);
    int fd = open("ack_test.json", O_RDONLY);
    if(fd < 0){
        printf("bad file\n");
        exit(1);
    }

    Process *proc = new Process(NULL, WD_DISABLED);

    MissionSocket ms = MissionSocket(fd, proc, &ack_cb, &gs_cb, &canc_cb, &wd_cb);

    //TO DO allow specification of time to schedule sending requests
    EVT_sched_add(proc->event_manager()->state(), EVT_ms2tv(60 * 1000),&request_cb, (void *)&ms);

    add_time(ms, 12, 13, 101);
    add_time(ms, 23, 26, 102);
    add_time(ms, 45, 55, 101);
    //ms.queue_withdrawl_request(2);
    ms.send_time_request();

    proc->event_manager()->EventLoop();

}