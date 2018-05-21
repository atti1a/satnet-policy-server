#include "mission_server.h"
#include <stdlib.h>
#include <stdio.h>

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

void MissionSocket::parse_ack(Value& ack_list)
{
   for(int i = 0; i < ack_list.Size(); i++){
      if(ack_list[i].HasMember("reqID") && ack_list[i]["reqID"].IsInt() && ack_list[i].HasMember("ackType") && ack_list[i]["ackType"].IsBool()){
         //check withdrawl case
         if(ack_list[i].HasMember("withdrawl") && ack_list[i]["withdrawl"].IsBool() && ack_list[i]["withdrawl"].GetBool()){
            //TODO call time request withdrawl callback
         }
         else{
            //ack callback
            resp_cb(ack_list[i]["reqID"].GetInt(), ack_list[i]["ackType"].GetBool());
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
         if(gs_list[i].HasMember("gsID") && gs_list[i].HasMember("lat") && gs_list.HasMember("long")){
            struct GroundStationInfo gs = {gs_list[i]["gsID"].GetInt(), 
               gs_list[i]["lat"].GetFloat(), gs_list[i]["long"].GetFloat()};
            gs_info.push_back(gs);
         }
         else{
            //invalid, ignore
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
   if(d["type"] == "ack"){
      printf("parsing ack\n");
      if(!d.HasMember("data") || !d["data"].IsArray()){
         printf("Missing ACK list\n");
         return size_parsed;
      }
      parse_ack(d["data"]);
   }
   //expect to see a vector of all groundstations that are available
   else if(d["type"] == "gs"){
      printf("parsing gs\n");
      if(!d.HasMember("data") || !d["data"].IsArray()){
         printf("Missing groundstation list\n");
         return size_parsed;
      }
      parse_gs_list(d["data"]);
   }
   else if(d["type"] == "cancel"){
      if(!d.HasMember("data") || ! d["data"].IsObject()){
         printf("Invalid cancel json object\n");
         return size_parsed;
      }
      parse_cancel(d["data"]);
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

//constructor
MissionSocket::MissionSocket(int socketFD, Process *proc, response_cb resp_cb, gs_update_cb gs_cb, cancel_cb canc_cb)
{
   this->proc = proc;
   this->socketFD = socketFD;
   this->resp_cb = resp_cb;
   this->gs_cb = gs_cb;
   this->canc_cb = canc_cb;
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

//adds a time request to the block of time requests to be sent
//returns 0 on success
int MissionSocket::queue_time_reqest(time_t start, time_t end, int gsID)
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

   writer.String("data");
   writer.StartArray();
   for(int i = 0; i < queued_requests.size(); i++){
      writer.StartObject();

      writer.String("reqID");
      writer.Int(queued_requests[i].reqID);

      writer.String("gsID");
      writer.Int(queued_requests[i].gsID);

      if(!queued_requests[i].withdrawl){
         writer.String("start");
         writer.Int(queued_requests[i].start);

         writer.String("end");
         writer.Int(queued_requests[i].end);
      }

      writer.String("withdrawl");
      writer.Bool(queued_requests[i].withdrawl);

      writer.EndObject();
      numSent ++;
   }
   writer.EndArray();

   writer.EndObject();

   //copy over to send buffer
   send_mess_len += sb.GetSize();
   if(send_mess_len + send_buf_pos > send_buf_size){
      //first try shifting buffer to make room
      memcpy(send_buf, send_buf + send_buf_pos, send_buf_size - send_buf_pos);
      send_buf_pos = 0;
   }
   if(send_mess_len + send_buf_pos > send_buf_size){
      //realloc more space
      send_buf_size += sb.GetSize();
      send_buf = (char *)realloc(send_buf, send_buf_size);
   }
   memcpy(send_buf + send_buf_pos, sb.GetString(), sb.GetSize());

   if(send_evt == 0){
      send_evt = EVT_fd_add(proc->event_manager()->state(), socketFD, EVENT_FD_WRITE, &write_cb, this);
   }

   queued_requests.clear();
   return numSent;
}


