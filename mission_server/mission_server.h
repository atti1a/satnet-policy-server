#ifndef MISSION_SERVER
#define MISSION_SERVER

#include <time.h>
#include <string.h>
#include <vector>
#include <polysat/polysat.h>
#include "rapidjson/document.h"
#include "rapidjson/error/en.h"
using namespace rapidjson;

typedef void (*response_cb)(int reqID, bool accepted);
typedef void (*cancel_cb)(int reqID);
typedef void (*gs_update_cb)(std::vector<struct GroundStationInfo>& gs_list);

struct TimeRequest
{
   int reqID;
   int gsID;
   time_t start;
   time_t end;
   bool withdrawl;
};

struct GroundStationInfo
{
    float lat;
    float lon;
    int gsID;
    //TO DO other info
};

class MissionSocket
{
   public:
   MissionSocket(int socketFD, Process *proc, response_cb resp_cb, gs_update_cb gs_cb, cancel_cb canc_cb);
   //sends all queued time requests, returns number of requests sent
   int send_time_request();
   //queues a time request to be sent to policy server (send using send_time_request())
   //returns a request ID that should be saved by the user and will be returned in the callback once a response is received
   int queue_time_reqest(time_t start, time_t end, int gsID);
   //same as queue_time_request() except it withdrawls a given time
   //returns back the request ID
   int queue_withdrawl_request(int reqID);
   


   private:
   //private functions
   int attempt_parse(char *buff);
   void parse_ack(Value& ack_list);
   void parse_gs_list(Value& gs_list);
   void parse_cancel(Value& cancel);
   static int read_cb(int fd, char type, void *arg);
   static int write_cb(int fd, char type, void *arg);

   //list of request that are queued to be sent together
   std::vector<struct TimeRequest>  queued_requests;

   Process *proc;
   int socketFD;
   response_cb resp_cb;
   gs_update_cb gs_cb;
   cancel_cb canc_cb;

   int nextReqID;

   //vars for sending data
   char send_evt;
   char *send_buf;
   int send_buf_pos;
   int send_buf_size;
   int send_mess_len;

   //vars for receiving data
   char *recv_buf;
   int recv_buf_pos;

   //save ground stations as they come in 
   std::vector<struct GroundStationInfo> gs_info;
};



#endif
