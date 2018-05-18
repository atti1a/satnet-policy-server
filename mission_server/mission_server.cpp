#include "mission_server.h"
#include <stdlib.h>
#include <stdio.h>

#define SND_BUF_SIZE 1500
#define RCV_BUF_SIZE 1500

int MissionSocket::parse_ack(Value& ack_list)
{
   for(int i = 0; i < ack_list.Size(); i++){
      if(ack_list[i].HasMember("reqID") && ack_list[i].HasMember("ackType") && ack_list[i]["ackType"].IsBool()){
         //check withdrawl case
         if(ack_list[i].HasMember("withdrawl") && ack_list[i]["withdrawl"].IsBool() && ack_list[i]["withdrawl"].GetBool()){
            //TODO call time request withdrawl callback
         }
         else if(ack_list[i].HasMember("start") && ack_list[i]["start"].IsInt() && ack_list[i].HasMember("end") && ack_list[i]["end"].IsInt()
               && ack_list[i].HasMember("gsID") && ack_list[i]["gsID"].IsInt()){
            //ack callback
            ack_cb(ack_list[i]["start"].GetInt(), ack_list[i]["end"].GetInt(), ack_list[i]["gsID"].GetInt(), ack_list[i]["ackType"].GetBool());
         }
         else{
            //invalid, ignore
         }

      }
      else{
         //invalid, ignore
      }
   }
}

int MissionSocket::parse_gs_list(Value& gs_list)
{
      for(int i = 0; i < gs_list.Size(); i++){
            printf("Item %d in gs list", i);
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
      parse_gs_list(d["data"]);
   }
   else{
      printf("Invalid header type\n");
   }
   return size_parsed;
}

int MissionSocket::read_cb(int fd, char type, void *arg)
{
   MissionSocket *ms = (MissionSocket *)arg;

   //int ret = read(fd, ms->recv_buf + ms->recv_buf_pos, RCV_BUF_SIZE - ms->recv_buf_pos);
   int ret = read(fd, ms->recv_buf + ms->recv_buf_pos, 12);
   if(ret < 0){
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

   return EVENT_KEEP;

   //TO DO
   MissionSocket *ms = (MissionSocket *)arg;
   int ret = write(fd, ms->send_buf + ms->send_buf_pos, ms->mess_len);
   if(ret < 0){
      printf("Error writing\n");
      return EVENT_REMOVE;
   }
   else if(ret < ms->mess_len){
      return EVENT_KEEP;
   }

   int bytes_parsed;

   while(bytes_parsed < ms->mess_len){
      //shift buffer to remove bytes that were sent
      memcpy(ms->send_buf, ms->send_buf + bytes_parsed, ms->recv_buf_pos - bytes_parsed);
      ms->recv_buf_pos -= bytes_parsed;
      memset(ms->recv_buf + ms->recv_buf_pos, 0, RCV_BUF_SIZE - ms->recv_buf_pos);
   }


   return EVENT_KEEP;
}

//constructor
MissionSocket::MissionSocket(int socketFD, Process *proc, ack_callback cb)
{
   this->proc = proc;
   this->socketFD = socketFD;
   ack_cb = cb;
   curState = header;
   EVT_fd_add(proc->event_manager()->state(), socketFD, EVENT_FD_READ, &read_cb, this);
   nextReqID = 1;
   //send buffer management
   send_buf = (char *)malloc(SND_BUF_SIZE);
   memset(send_buf, 0, SND_BUF_SIZE);
   send_buf_pos = 0;
   mess_len = 0;
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
}

//encodes and sends off all queued time requests
//returns number of requests to be sent, does not send immediately, uses select loop
int MissionSocket::send_time_request()
{
   //TODO won't work if there is already something in the buffer
   sendEvt = EVT_fd_add(proc->event_manager()->state(), socketFD, EVENT_FD_WRITE, &write_cb, this);
}


