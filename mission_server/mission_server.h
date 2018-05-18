#ifndef MISSION_SERVER
#define MISSION_SERVER

#include <time.h>
#include <string.h>
#include <vector>
#include <polysat/polysat.h>
#include "rapidjson/document.h"
#include "rapidjson/error/en.h"
using namespace rapidjson;

typedef void (*ack_callback)(time_t start, time_t end, int gsID, bool accepted);

enum ReadState {header, ack, gs};

struct TimeRequest
{
   int reqID;
   int gsID;
   time_t start;
   time_t end;
   bool withdrawl;
};

class MissionSocket
{
   public:
   MissionSocket(int socketFD, Process *proc, ack_callback cb);
   int send_time_request();
   int queue_time_reqest(time_t start, time_t end, int gsID);
   static int read_cb(int fd, char type, void *arg);

   private:
   std::vector<struct TimeRequest>  queued_requests;

   Process *proc;
   int socketFD;
   ack_callback ack_cb;
   ReadState curState;

   int nextReqID;

   //vars for sending data
   char sendEvt = 0;
   char *send_buf;

   //vars for receiving data
   char *recv_buf;
   int recv_buf_pos;

   int attempt_parse(char *buff);
   int parse_ack(Value& ack_list);
};

#endif
