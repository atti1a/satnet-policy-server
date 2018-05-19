#include "mission_server.h"
#include <fcntl.h>
#include <stdio.h>

void ack_cb(time_t start, time_t end, int gsID, bool accepted)
{
    if(accepted){
        printf("YAY, using time on gs %d from %ld to %ld\n", gsID, start, end);
    }
    else{ 
        printf("NOOOO, can't use time on gs %d from %ld to %ld\n", gsID, start, end);
    }
}

int main(int argc, char **argv)
{
    int fd = open("ack_test.json", O_RDONLY);

    Process *proc = new Process(NULL, WD_DISABLED);

    MissionSocket ms = MissionSocket(fd, proc, &ack_cb);

    proc->event_manager()->EventLoop();

}