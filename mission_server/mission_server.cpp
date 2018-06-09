#include "mission_server.h"
#include <stdlib.h>
#include <stdio.h>
#include <sstream>

#include "rapidjson/writer.h"
#include <string>
using namespace rapidjson;

#define SND_BUF_SIZE 1500
#define RCV_BUF_SIZE 1500


/*
* TODO
* track sent requests in hashmap for lookup on ack
* timeout on requests?
* parse gs info
* make gs info available to user
*/
//constructor
MissionSocket::MissionSocket(int socketFD, Process *proc, response_cb resp_cb, 
      gs_update_cb gs_cb, cancel_cb canc_cb, withdrawl_cb wd_cb)
{
   this->proc = proc;
   this->socketFD = socketFD;
   this->resp_cb = resp_cb;
   this->gs_cb = gs_cb;
   this->canc_cb = canc_cb;
   this->wd_cb = wd_cb;
   EVT_fd_add(proc->event_manager()->state(), socketFD, EVENT_FD_READ, &read_cb, this);
   nextReqID = 1;

   //send buffer management
   send_evt = 0;
   send_buf_pos = 0;
   send_mess_len = 0;
   send_buf_size = SND_BUF_SIZE;
   send_buf = (char *)malloc(send_buf_size);
   memset(send_buf, 0, send_buf_size);

   //receive buffer management
   recv_buf = (char *)malloc(RCV_BUF_SIZE);
   memset(recv_buf, 0, RCV_BUF_SIZE);
   recv_buf_pos = 0;
}


//set all communication vars needed to send json
void MissionSocket::set_comm_vars(int gid, std::string ss, std::string la, int lp, std::string ln){
   //comms vars
   shared_secret = ss;
   global_id = gid;
   local_addr = la;
   local_port = lp;
   name = ln;
}


void MissionSocket::parse_resp(Value& resp_list)
{
   for(int i = 0; i < resp_list.Size(); i++){
      if(resp_list[i].HasMember("reqID") && resp_list[i]["reqID"].IsInt() && resp_list[i].HasMember("ack") && resp_list[i]["ack"].IsBool()){
         //check withdrawl case
         if(resp_list[i].HasMember("wd") && resp_list[i]["wd"].IsBool() && resp_list[i]["wd"].GetBool()){
            wd_cb(resp_list[i]["reqID"].GetInt(), resp_list[i]["ack"].GetBool());
         }
         else{
            //ack callback
            resp_cb(resp_list[i]["reqID"].GetInt(), resp_list[i]["ack"].GetBool());
         }
      }
      else{
         //invalid, ignore
      }
   }
}

void MissionSocket::parse_gs_list(Value& gs_list)
{
   //clear previous gs list
   gs_info.clear();
   for(int i = 0; i < gs_list.Size(); i++){
         if(gs_list[i].HasMember("gsID") && gs_list[i].HasMember("lat") && gs_list[i].HasMember("long")){
            struct GroundStationInfo gs = {gs_list[i]["gsID"].GetInt(), 
               gs_list[i]["lat"].GetFloat(), gs_list[i]["long"].GetFloat()};
            gs_info.push_back(gs);
         }
         else{
            //invalid, ignore
            printf("Parsed GS element %i is invalid", i);
         }
   }

   gs_cb(gs_info);
}

void MissionSocket::parse_cancel(Value& cancel)
{
   if(cancel.HasMember("reqID") && cancel["reqID"].IsInt()){
      canc_cb(cancel["reqID"].GetInt());
   }
}

int MissionSocket::attempt_parse(char *buff)
{
   StringStream ss(buff);

   Document d;
   d.ParseStream<kParseStopWhenDoneFlag>(ss);
   size_t size_parsed = ss.Tell();
   if(d.HasParseError()){
      if(size_parsed == strlen(buff)){
         //just not done reading json yet
         return 0;
      }
      else{
         //actual error with json formatting
         printf("Error %u (offset %u): %s\n", d.GetParseError(), (unsigned)d.GetErrorOffset(), GetParseError_En(d.GetParseError()));
         return -1;
      }
   }

   //check header for type
   if(!d.HasMember("type")){
      printf("Missing type, ignoring json structure\n");
      return size_parsed;
   }
   if(d["type"] == "RESP"){
      printf("parsing response\n");
      if(!d.HasMember("respList") || !d["respList"].IsArray()){
         printf("Missing ACK list\n");
         return size_parsed;
      }
      parse_resp(d["respList"]);
   }
   if(d["type"] == "PS_INIT"){
      printf("Got a PS_INIT packet\n");
   }
   //expect to see a vector of all groundstations that are available
   else if(d["type"] == "GS"){
      printf("parsing gs\n");
      if(!d.HasMember("gsList") || !d["gsList"].IsArray()){
         printf("Missing groundstation list\n");
         return size_parsed;
      }
      parse_gs_list(d["gsList"]);
   }
   else if(d["type"] == "cancel"){
      if(!d.HasMember("cancelList") || ! d["cancelList"].IsObject()){
         printf("Invalid cancel json object\n");
         return size_parsed;
      }
      parse_cancel(d["cancelList"]);
   }
   else{
      printf("Invalid header type\n");
   }
   return size_parsed;
}

int MissionSocket::read_cb(int fd, char type, void *arg)
{
   MissionSocket *ms = (MissionSocket *)arg;

   int ret = read(fd, ms->recv_buf + ms->recv_buf_pos, RCV_BUF_SIZE - ms->recv_buf_pos);
   if(ret < 0){
      //TODO handle error well
      printf("Error reading\n");
      return EVENT_REMOVE;
   }
   else if(ret == 0){
      return EVENT_KEEP;
   }

   ms->recv_buf_pos += ret;

   int bytes_parsed;
   while((bytes_parsed = ms->attempt_parse(ms->recv_buf)) > 0){
      //shift buffer to remove bytes that were parsed
      memcpy(ms->recv_buf, ms->recv_buf + bytes_parsed, ms->recv_buf_pos - bytes_parsed);
      ms->recv_buf_pos -= bytes_parsed;
      memset(ms->recv_buf + ms->recv_buf_pos, 0, RCV_BUF_SIZE - ms->recv_buf_pos);
   }
   if(bytes_parsed == -1){
      //TODO error, reset socket
   }

   return EVENT_KEEP;
}

int MissionSocket::write_cb(int fd, char type, void *arg)
{
   MissionSocket *ms = (MissionSocket *)arg;
   int ret = write(fd, ms->send_buf + ms->send_buf_pos, ms->send_mess_len);
   if(ret < 0){
      //TODO handler error well
      printf("Error writing\n");
      return EVENT_REMOVE;
   }
   
   ms->send_buf_pos += ret;
   ms->send_mess_len -= ret;

   if(ms->send_mess_len == 0){
      //case where there is no more to send
      ms->send_evt = 0;
      ms->send_buf_pos = 0;
      return EVENT_REMOVE;
   }

   return EVENT_KEEP;
}

//adds a time request to the block of time requests to be sent
//returns 0 on success
int MissionSocket::queue_time_request(time_t start, time_t end, int gsID)
{
   struct TimeRequest tr = {nextReqID, gsID, start, end, false};
   nextReqID += 1;

   queued_requests.push_back(tr);

   return tr.reqID;
}

int MissionSocket::queue_withdrawl_request(int reqID)
{
   struct TimeRequest tr = {reqID, 0, 0, 0, true};

   queued_requests.push_back(tr);
   return tr.reqID;
}

//add in the send init request
void MissionSocket::send_init()
{
      printf("Sending initialization to policy server\n");
      StringBuffer sb;
      Writer<StringBuffer> writer(sb);

      writer.StartObject();

      writer.String("type");
      writer.String("MS_INIT");

      writer.String("msID");
      writer.Int(global_id);

      writer.String("name");
      writer.String(name.c_str());

      writer.String("ip");
      writer.String(local_addr.c_str());
      writer.String("port");
      writer.Int(local_port);
      writer.String("psk");
      writer.String(shared_secret.c_str());

      writer.EndObject();

      //copy over to send buffer
      send_mess_len += sb.GetSize() + 1; //add in space for newline
      if (send_mess_len + send_buf_pos > send_buf_size)
      {
            //first try shifting buffer to make room
            memcpy(send_buf, send_buf + send_buf_pos, send_buf_size - send_buf_pos);
            send_buf_pos = 0;
      }
      if (send_mess_len + send_buf_pos > send_buf_size)
      {
            //realloc more space
            send_buf_size += sb.GetSize() + 1; //plus newline
            send_buf = (char *)realloc(send_buf, send_buf_size);
      }
      memcpy(send_buf + send_buf_pos, sb.GetString(), sb.GetSize());
      memcpy(send_buf + send_buf_pos + sb.GetSize(), "\n", 1); //tack on the newline as a terminator

      if (send_evt == 0)
      {
            send_evt = EVT_fd_add(proc->event_manager()->state(), socketFD, EVENT_FD_WRITE, &write_cb, this);
      }
}



//add a callback to send_time_request at certain time
//encodes and sends off all queued time requests
//returns number of requests to be sent, does not send immediately, uses select loop
int MissionSocket::send_time_request()
{
   int numSent;
   StringBuffer sb;
   Writer<StringBuffer> writer(sb);

   writer.StartObject();

   writer.String("type");
   writer.String("TR");

   writer.String("trList");
   writer.StartArray();
   for(int i = 0; i < queued_requests.size(); i++){
      writer.StartObject();

      writer.String("reqID");

      //do some magic to make the ID string
      std::stringstream id_str;
      id_str << global_id << "-" << queued_requests[i].reqID;
      writer.String(id_str.str().c_str());

      writer.String("gsID");
      writer.Int(queued_requests[i].gsID);

      if(!queued_requests[i].withdrawl){
         writer.String("start");
         writer.Int(queued_requests[i].start);

         writer.String("end");
         writer.Int(queued_requests[i].end);
      }

      writer.String("wd");
      writer.Bool(queued_requests[i].withdrawl);

      writer.EndObject();
      numSent ++;
   }
   writer.EndArray();

   writer.EndObject();

   //copy over to send buffer
   send_mess_len += sb.GetSize() + 1; //add in space for newline
   if(send_mess_len + send_buf_pos > send_buf_size){
      //first try shifting buffer to make room
      memcpy(send_buf, send_buf + send_buf_pos, send_buf_size - send_buf_pos);
      send_buf_pos = 0;
   }
   if(send_mess_len + send_buf_pos > send_buf_size){
      //realloc more space
      send_buf_size += sb.GetSize() + 1; //plus newline
      send_buf = (char *)realloc(send_buf, send_buf_size);
   }
   memcpy(send_buf + send_buf_pos, sb.GetString(), sb.GetSize());
   memcpy(send_buf + send_buf_pos + sb.GetSize(), "\n", 1); //tack on the newline as a terminator

   if(send_evt == 0){
      send_evt = EVT_fd_add(proc->event_manager()->state(), socketFD, EVENT_FD_WRITE, &write_cb, this);
   }

   queued_requests.clear();
   return numSent;
}


