#include "mission_server.h"
#include <fcntl.h>
#include <stdio.h>
#include <map>


enum TR_state {SENT, ACCEPT, REJECT, CANCEL, WITHDRAWL};

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
    //DO something
}

void canc_cb(int reqID)
{

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
    time_requests[reqID].state = WITHDRAWL;
}

int main(int argc, char **argv)
{
    //int fd = open("ack_test.json", O_RDWR | O_APPEND);
    int fd = open("ack_test.json", O_RDONLY);
    if(fd < 0){
        printf("bad file\n");
        exit(1);
    }

    Process *proc = new Process(NULL, WD_DISABLED);

    MissionSocket ms = MissionSocket(fd, proc, &ack_cb, &gs_cb, &canc_cb);

    add_time(ms, 12, 13, 101);
    add_time(ms, 23, 26, 102);
    add_time(ms, 45, 55, 101);
    ms.queue_withdrawl_request(2);
    ms.send_time_request();

    proc->event_manager()->EventLoop();

}