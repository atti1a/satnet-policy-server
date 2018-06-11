import json
from collections import defaultdict
import sched, time

class Server(object):
   def __init__(self, name, server_id, conn):
      self.name = name
      self.uuID = server_id
      self.conn = conn

   def __hash__(self):
      return self.uuID
   def __eq__(self, other):
      if isinstance(other, Server):
         return self.uuID == other.uuID
      elif isinstance(other, int):
         return self.uuID == other
      else:
         return False
   def __ne__(self, other):
      return not self == other


class MissionServer(Server):
   """mission server object

   Attribures:
      name (string): the name of this mission server
      ms_id (int): the unique id of this mission server
      conn : connection reference to mission server
   """
   def __init__(self, name, ms_id, conn):
      Server.__init__(self, name, ms_id, conn)


class PolicyServer(Server):
   """policy server object

   Attribures:
      name (string): the name of this policy server
      ps_id (int): the unique id of this policy server
   """
   def __init__(self, name, ps_id, conn):
      Server.__init__(self, name, ps_id, conn)
      self.msList = set()

class GroundStation(object):
   def __init__(self, gsID, lat, lon, netLocation=None):
      self.gsID = gsID
      self.lat = lat
      self.lon = lon
      self.netLocation = netLocation

   def __hash__(self):
      return self.gsID
   def __eq__(self, otherGS):
      if isinstance(otherGS, GroundStation):
         return self.gsID == otherGS.gsID
      elif isinstance(otherGS, int):
         return self.gsID == otherGS
      else:
         return False
   def __ne__(self, otherGS):
      return not self == otherGS


class Schedule(object):
   """schedule object

   Attributes:
      server : reference to MissionServer or PolicyServer that sent this request
      gs_id (int): the id of the groundstation related to this schedule
      ms_id (int): the id of the mission server related to this schedule
      start (int): start time of schedule
      end (int): end time of the schedule
   """
   def __init__(self, req_packet, server):
      self.requester = server
      self.reqID = req_packet['reqID']
      self.gsID = req_packet['gsID']
      self.start = req_packet['start']
      self.end = req_packet['end']
      self.eventID = -1

   def __hash__(self):
      return self.reqID
   def __eq__(self, otherSched):
      if isinstance(otherSched, Schedule):
         return self.gsID == otherSched.gsID
      elif isinstance(otherSched, str):
         return self.gsID == otherSched
      else:
         return False
   def __ne__(self, otherSched):
      return not self == otherSched

   def has_conflict(self, sched):
      """Tells you if the passed in schedule has a conflict with the current
      schedule object

      Args:
         schedule (schedule): another schedule object

      Returns: true if there is a conflict in the two schedules, false if not
      """
      # There's no conflict if its on another ground station
      if self.gsID != sched.gsID: return False

      ends_between = self.start <= sched.end and sched.end <= self.end
      starts_between = self.start <= sched.end and sched.end <= self.end
      starts_before_and_ends_after = sched.start <= self.start and self.end <= sched.end

      return ends_between or starts_between or starts_before_and_ends_after

def merge_dict_of_lists(d1, d2):
   """merges a dictionary that has a values of type list
      note: d1 must be a default dict type
   """
   if not d2: return
   for k, v in d2.iteritems():
      d1[k] += v

def build_gs_array(gs_set, other_gs=None):
      gs_arr = []
      for gs in gs_set:
         gs_arr.append({"gsID":gs.gsID, "lat":gs.lat, "long": gs.lon})

      if other_gs != None:
         for key, gs in other_gs.iteritems():
            gs_arr.append({"gsID":gs.gsID, "lat":gs.lat, "long": gs.lon})
      return gs_arr

class PS(object):
   """Contains all relevant logic and data necessary for gss

   Attributes:
      id (int): The id of the policy station

      schedules (schedule): set of schedules

      ms_set {int}: list of mission server ids connected to us

      gs_set {int}: list of groundstation ids connected to us
   """
   def __init__(self, scheduler):
      self.id = 0
      self.schedules = {}
      self.gs_set = set() #set of our ground station ids
      self.foreign_gs = {} #all other gs indexed on id, stores connection to reach that gs
      self.scheduler = scheduler
      self.peers = {} #dictionary of mission servers and policy servers, index by id

   def add_groundstation_local(self, gsId, lat, lon):
      self.gs_set.add(GroundStation(gsId, lat, lon, None))

   #def add_groundstation_foreign(self, gsId, lat, lon, conn):
   #   self.gs_set.add(GroundStation(gsId, lat, lon, conn))

   def conn2serverKey(self, conn):
      keys = [key for key, val in self.peers.iteritems() if val.conn == conn]

      if len(keys) == 0:
         return None
      return keys[0]

   def msID2conn(self, msID):
      if "ms"+str(msID) in self.peers.keys():
            return self.peers["ms"+str(msID)].conn
      return None


   def strip_gs_metadata(self, gs_metadata):
      """
      Strips down gs metadata packet, because we don't actually want to
      broadcast all info just the info that's necessary for other mission servers
      to make its decision

      Args:
         gs_metadata: the metadata packet we recieve from the gs
            (JSON object)

      Returns: stripped down gs metadata (JSON file to be sent)
      """

      # create stripped down metadata
      stripped_metadata = {}
      # NOTE i think we need the authority psID for this too if gsIDs aren't
      # unique globally
      required_fields_in_stripped_metadata = {
         'gsID',
         'lat',
         'long'
      }

      for required_field in required_fields_in_stripped_metadata:
         stripped_metadata[required_field] = gs_metadata[required_field]

      return stripped_metadata

   # NOTE need to update this so that we store all gs metadata, and forward all
   # info on any uddate
   def relay_stripped_gs_metadata(self, gs_metadata):
      """
      Event: on recieve of our own ground station metadata packet

      Strips the gs metadata into information other servers (mission)
      require in order to make a decision what gss it wants. (We don't
      want to share all of our gss data, just what's necessary). Then
      it relays this stripped gsd data to all connected servers
      (policy and mission).

      Args:
         gs_metadata: the metadata we recieve from the gs

      Returns: (destination, packet)
         destination: "servers" destination specifies that the packet will be sent
         to all connected servers (policy and mission) to our server (policy)

         packet: the stripped gs metadata is the packet that will be
         sent to all the servers (policy and mission)
      """
      stripped_gs_metadata = self.strip_gs_metadata(gs_metadata)

      return {"servers": stripped_gs_metadata}

   def fwd_stripped_gs_metadata(self, stripped_gs_metadata, conn):
      """
      Event: On receive of another school's stripped gs metadata packet
         from another school's server (policy)

      Forwards this gs metadata packet to its own servers (mission)

      Args:
         stripped_gs_metadata: a packet containing stripped metadata of
         some gs

      Returns: (destination, packet)
         destination: "mss" destination specifies that the packet will
         be sent to all connected servers (mission) to our server (policy)

         packet: the stripped gs metadata is the packet containing useful
         metadata regarding a gs that will be sent to all the servers
         (policy and mission)
      """

      for gs in stripped_gs_metadata["gsList"]:
         self.foreign_gs[gs["gsID"]] = GroundStation(gs["gsID"], gs["lat"], gs["long"], conn)

      return []
      #return {'all_servers': stripped_gs_metadata}

   def handle_withdrawl(self, gs_request):
      """checks if withdrawl reqID is actually in our schedule, if it does, we
      cancel it, if not, we send a nack
      """
      # Construct the withdrawl ack
      reqID = gs_request['reqID']
      ack = gs_request['reqID'] in self.schedules
      withdrawl_ack = {'reqID': reqID, 'ack' : ack, 'wd' : True}

      # Remove the schedule from the policy server
      self.scheduler.cancel(self.schedules[gs_request['reqID']].eventID)
      del self.schedules[gs_request['reqID']]

      return withdrawl_ack

   def has_priority(self, schedule_1, schedule_2):
      """ Given two schedule objects, return true if ms_id_1 has priority
      over ms_id_2, this implementation is left up to the school
      """
      # TODO implement priority method
      return schedule_1.reqID > schedule_2.reqID

   def cancel_schedules(self, schedules_to_be_canceled):
      """forms the cancel packets for schedules_to_be_canceled, and removes them from the PS's list
      of schedules
      """
      cancel_packets = defaultdict(list)
      for schedule in schedules_to_be_canceled:
         # Cancel the schedule by removing it from the policy servers schedule
         conn = self.peers[schedule.requester].conn #TODO what to do if lookup fails
         self.scheduler.cancel(schedule.eventID)
         del self.schedules[schedule.reqID]

         cancel_packets[conn].append({'reqID': schedule.reqID})

      return cancel_packets

   def handle_schedule_request(self, gs_request, conn):
      """tries to schedule a single request
      case 1: conflict --> nack
      case 2: conflict but has priority --> cancel to original schedule and ack
      case 3: no conflict --> ack
      """
      cancel_packets = None
      acking = True
      curr_req = Schedule(gs_request, self.conn2serverKey(conn))

      #check for conflicts
      conflicting_schedules = filter(curr_req.has_conflict, self.schedules.values())

      if len(conflicting_schedules) > 0:
         #build list of conflicts that are lower priority that the proposed request
         has_priority = lambda schedule: self.has_priority(curr_req, schedule)
         lower_priority_scheds = filter(has_priority, conflicting_schedules)

      # Case 2: we have conflicts, but we have priority over all those conflicts
         if len(lower_priority_scheds) == len(conflicting_schedules):
            # send cancel packet to those conflicts we're overriding
            cancel_packets = self.cancel_schedules(conflicting_schedules)
      # Case 1: we have some conflicting schedules and no priority over them, only case where ack is False
         else:
            acking = False
      # Case 3: implicit, if no conflicts we already have ack to true

      if acking:
         curr_req.eventID = self.scheduler.enterabs(curr_req.start, 1, self.control_gs_start, (curr_req,))
         self.schedules[curr_req.reqID] = curr_req

      ack = {'reqID': curr_req.reqID, 'ack': acking, 'wd': False}
      ack_packet = {conn: [ack]}

      return ack_packet, cancel_packets

   def unecessary_forward(self, gs_request):
      """tells you if this gs_request has already been fulfilled by our own
      groundstations so that we can filter some requests for other gs before
      sending it out

      but you can put any other heuristic to determine if a gs_request is unecessary
      """
      # If its a withdrawl, we forward it regardless
      if gs_request['wd']: return False

      # Else, we check if a request is already fulfilled by our own gs
      # isntantiate object just so we can use the method
      request = Schedule(gs_request, None)

      for schedule in self.schedules.values():
         if request.has_conflict(schedule): return True

      return False

   def format_packets(self, list_of_packet_dicts):
      list_name_mapping = {
         'CANCEL': 'cancelList',
         'GS': 'gsList',
         'RESP': 'respList',
         'TR': 'trList'
      }

      packets = defaultdict(list)
      for packet_type, packet in list_of_packet_dicts:
         for msg_type, packet_list in packet.iteritems():
            packets[msg_type].append({
               'type': packet_type,
               list_name_mapping[packet_type]: packet_list
            })

      return packets

   def meant_for_us(self, req_packet):
      """ returns true if a request packet is meant for us, if not, it should just be forwarded"""
      # if the packet is a withdrawl, and the reqID is in our list of schedules, then we can withdraw
      if req_packet['wd']:
         return req_packet['reqID'] in self.schedules
      # else its not a withdrowl, and we check that the request is for a GS we own
      elif not req_packet['wd']:
         return req_packet['gsID'] in self.gs_set

   def handle_requests(self, gs_requests, conn):
      """
      Event: On receive of a ground_station request packet for another school's
         ground station from our own server (mission)

      Forwards this gs request packet to corresponding servers (policy)

      Args:
         gs_requests: A list of ground station requests.

      Returns:
      """
      response_packets = defaultdict(list)
      cancel_packets = defaultdict(list)
      time_request_packets = defaultdict(list)

      for gs_request in gs_requests:
         if self.meant_for_us(gs_request):
            if gs_request['wd']:
               response_packets[conn].append(self.handle_withdrawl(gs_request))
            elif not gs_request['wd']:
               some_responses, some_cancels = self.handle_schedule_request(gs_request, conn)
               merge_dict_of_lists(response_packets, some_responses)
               merge_dict_of_lists(cancel_packets, some_cancels)

         elif not self.meant_for_us(gs_request) or not self.unecessary_forward(gs_request):
            # TODO no way to know where to forward withdrawl too without gsData
            if gs_request['wd']:
               connection = self.schedules[gs_request['reqID']].conn

               time_request_packets[connection].append(gs_request)
            elif not gs_request['wd']:
               if gs_request in self.foreign_gs.keys():
                  connection = self.foreign_gs[gs_request['gsID']].netLocation
                  gs_request["reqID"] = self.conn2serverKey(conn) + "-" + gs_request["reqID"]

                  time_request_packets[connection].append(gs_request)
               else: #groundstation doesn't exist, nack
                  response_packets[conn].append({"reqID":gs_request["reqID"], "ack":False, "wd":False})

      unformatted_packet_sets = []
      if response_packets:     unformatted_packet_sets.append(('RESP', response_packets))
      if cancel_packets:       unformatted_packet_sets.append(('cancel', cancel_packets))
      if time_request_packets: unformatted_packet_sets.append(('TR', time_request_packets))

      return self.format_packets(unformatted_packet_sets)
   def fwd_responses_to_ms(self, responses):

      packets = defaultdict(list)

      for resp in responses:
         #strip off the mission id that was added
         reqID = resp["reqID"]
         msID = resp["reqID"].split('-', )[0]
         reqID = reqID[len(msID)+1:]
         conn = self.peers[str(msID)].conn #TODO may fail lookup
         resp["reqID"] = reqID
         packets[conn].append(resp)
         packets["a"].append(resp)

      combining_packets = []
      if packets: combining_packets.append(('RESP', packets))

      ret = self.format_packets(combining_packets)
      return ret

   def fwd_cancel_to_ms(self, cancels):

      packets = defaultdict(list)

      for can in cancels:
         #strip off the mission id that was added
         msID = can["reqID"].split('-', )[0]
         reqID = can[len(msID)+1:]
         conn = self.peers["ms" + str(msID)].conn #TODO may fail lookup
         can["reqID"] = reqID
         packets[conn].append(can)

      combining_packets = []
      if packets: combining_packets.append(('CANCEL', packets))

      ret = self.format_packets(combining_packets)
      return ret


   #takes a Schedule object as an argument
   def control_gs_start(self, request):
      """
      Event: On recieve time notification from our gs_schedules

      Creates the packet that tells the gs to connect to the server
      (mission) for the time specified by our schedule

      Args:
         authority_ps: the server (policy) responsible for the server
         (mission) that the gs should connect to

         ms: the server (misison) that the gs should connect
         to

         time_range: the time range for which the ground station should be
         connected to the server (mission)

      Returns: tuple (destination, packet)
         destination: "gs" destination specifies a message towards the
         gs related to the event call

         packet: "connection_packet" the packet with necessary information for the
         ground station to connect to he corresponding server (mission)
      """

      #TODO check for mission_id to ip mapping

      #TODO ??
      #connection_packet = {
      #   'authority_ps' : 1,
      #   'ms' : request.msID,
      #   'time_range': request.start
      #}

      #schedule the time end event
      request.eventID = self.scheduler.enterabs(request.end, 1, self.control_gs_end, (request,))

      #return ("gs", connection_packet)
      return None

   def control_gs_end(self, request):
      # TODO remove this completed time request from schedules
      pass

   def fwd_cancel(self, cancel_packets):
      return {cancel_packets['msID']: cancel_packets}

   def handle_response(self, response_packet):
      return ('fwd', response_packet)

   def ms_init(self, data, conn):
      ms = MissionServer(data["name"], data["msID"], conn)
      key = "ms" + str(data["msID"])

      self.peers[key] = ms

      gs_list = {}
      gs_list[conn] = [{
         "type":"GS",
         "gsList":build_gs_array(self.gs_set, self.foreign_gs)
      }]

      return gs_list

   def ps_init(self, data, conn):
      ps = PolicyServer(data["name"], data["psID"], conn)
      key = "ps" + str(data["psID"])

      self.peers[key] = ps

      gs_list = {}
      gs_list[conn] = [{
         "type":"GS",
         "gsList":build_gs_array(self.gs_set)
      }]

      return gs_list
