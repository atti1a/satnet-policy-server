import json
from collections import defaultdict
import sched, time

class MissionServer(object):
   """mission server object

   Attribures:
      name (string): the name of this mission server
      ms_id (int): the unique id of this mission server
   """
   def __init__(self, name, id):
      self.name = name
      self.uuid = id

   def __hash__(self):
      return self.uuid

class PolicyServer(object):
   """policy server object

   Attribures:
      name (string): the name of this policy server
      ms_id (int): the unique id of this policy server
   """
   def __init__(self, name, id):
      self.name = name
      self.uuid = id

   def __hash__(self):
      return self.uuid

class GroundStation(object):
      def __init__(self, id, lat, long):
            self.id = id
            self.lat = lat
            self.long = long

class Schedule(object):
   """schedule object

   Attributes:
      gs_id (int): the id of the groundstation related to this schedule
      ms_id (int): the id of the mission server related to this schedule
      start (int): start time of schedule
      end (int): end time of the schedule
   """
   def __init__(self, req_packet, connRef):
      self.connRef = connRef
      self.reqID = req_packet['reqID']
      self.gsID = req_packet['gsID']
      self.start = req_packet['start']
      self.end = req_packet['end']
      self.eventID = -1

   def __hash__(self):
      return self.reqID

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
   for k, v in d2.iteritems():
      d1[k] += v

def build_gs_array(gs_set):
      gs_arr = []
      for gs in gs_set:
         gs_arr.append({"gsID":gs.id, "lat":gs.lat, "long": gs.long})
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
      self.ms_set = set()
      self.gs_set = set() #set of our ground station ids
      self.foreign_gs = {} #all other gs indexed on id, stores connection to reach that gs
      self.scheduler = scheduler

   def add_groundstation(self, id, lat, long):
      self.gs_set.add(GroundStation(id, lat, long))

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

   def fwd_stripped_gs_metadata(self, stripped_gs_metadata, connRef):
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

      for gs in stripped_gs_metadata:
         self.foreign_gs[gs["gsID"]] = connRef

      return {'all_servers': stripped_gs_metadata}

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

   def has_priority(self, req_id_1, req_id_2):
      """ Given two mission server ids, return true if ms_id_1 has priority
      over ms_id_2, this implementation is left up to the school
      """
      # FOR NOW
      return req_id_1 > req_id_2

   def handle_cancel(self, cancel_scheds):
      """does the requested cancels
      """
      cancel_forwards = defaultdict(list)
      for cancel_id, cancel_sched in cancel_scheds.iteritems():
         # Cancel the schedule by removing it from the policy servers schedule
         # But also get it so we can get the msID

         #Forward cancel to corresponding mission server
         reqID = cancel_id

         connRef = cancel_sched.connRef
         self.scheduler.cancel(cancel_sched.eventID)
         del self.schedules[cancel_id]

         cancel_forwards[connRef].append({'reqID': reqID})

      return cancel_forwards

   def handle_schedule_request(self, gs_request, connRef):
      """tries to schedule a single request
      conflict --> nack
      conflict but has priority --> cancel to original schedule and ack
      no conflict --> ack
      """
      responses = defaultdict(list)
      cancels = defaultdict(list)
      acking = False

      # create a schedule object
      request = Schedule(gs_request, connRef)
      reqID = request.reqID

      #check for conflicts
      conflicting_schedules = {}
      for reqID, sched in self.schedules.iteritems():
         if request.has_conflict(sched):
            conflicting_schedules[reqID] = sched

      # If we able to acquire conflicting schedules, we have a conflict
      if len(conflicting_schedules) > 0:
         #build list of conflicts that are lower priority that the proposed request
         lower_priority_scheds = {}
         for reqID, conflict in conflicting_schedules.iteritems():
            if self.has_priority(conflict.reqID, reqID):
               lower_priority_scheds[reqID] = conflict

         # If we have a conflict, but have priority over all those conflicts
         if len(lower_priority_scheds) == len(conflicting_schedules):
            acking = True

            # send cancel packet to those conflicts we're overriding
            merge_dict_of_lists(cancels, self.handle_cancel(conflicting_schedules))

      # Else, we have no conflict and we can just send an ack
      else:
         acking = True

      if acking:
         request.eventID = self.scheduler.enterabs(request.start, 1, self.control_gs_start, (request))
         self.schedules[gs_request['reqID']] = request

      ack = {'reqID': gs_request['reqID'], 'ack': acking, 'wd': False}
      responses[connRef].append(ack)

      return responses, cancels

   def already_scheduled_with_own_gs(self, gs_request):
      """tells you if this gs_request has already been fulfilled by our own
      groundstations so that we can filter some requests for other gs before
      sending it out"""
      # isntantiate object just so we can use the method
      request = Schedule(gs_request, None)

      for reqID, schedule in self.schedules.iteritems():
         if request.has_conflict(schedule): return True

      return False

   def format_packets(self, list_of_packet_dicts):
      list_name_mapping = {
         'cancel': 'cancelList',
         'GS': 'gsList',
         'RESP': 'respList',
         'TR': 'trList'
      }

      packets = {}
      for packet_type, packet in list_of_packet_dicts:
         for msg_type, packet_list in packet.iteritems():
            packets[msg_type] = {'type': packet_type, list_name_mapping[packet_type]: packet_list}

      return packets

   def handle_requests(self, gs_requests, connRef):
      """
      Event: On receive of a ground_station request packet for another school's
         ground station from our own server (mission)

      Forwards this gs request packet to corresponding servers (policy)

      Args:
         gs_requests: A list of ground station requests.

      Returns:
      """
      # requests for our groundstations
      is_our_gs = lambda gs_request: gs_request['gsID'] in self.gs_set
      requests_for_our_gs = filter(is_our_gs, gs_requests)

      responses, cancels = defaultdict(list), defaultdict(list)
      for gs_request in requests_for_our_gs:
         if gs_request['wd']:
            gsConnection = self.foreign_gs[gs_request['gsID']]
            responses[gsConnection].append(self.handle_withdrawl(gs_request))
         else:
            some_responses, some_cancels = self.handle_schedule_request(gs_request, connRef)
            merge_dict_of_lists(responses, some_responses)
            merge_dict_of_lists(cancels, some_cancels)


      # requests for other groundstations, we also filter out requests that we
      # can already fulfill with our own groundstations before sending it out,
      # we can do more filtering if necessary
      is_not_our_gs = lambda gs_request: gs_request['gsID'] in self.gs_set
      requests_for_other_gs = filter(is_not_our_gs, gs_requests)

      # NOTE how will we know what policy servers to send these requests too
      fwd_filtered_requests_for_other_gs = \
         filter(self.already_scheduled_with_own_gs, requests_for_other_gs)

      time_requests = defaultdict(list)
      for req in fwd_filtered_requests_for_other_gs:
         time_requests[self.foreign_gs[req["gsID"]]].append(req)


      combining_packets = []
      if responses: combining_packets.append(('RESP', responses))
      if cancels: combining_packets.append(('cancel', responses))
      if time_requests: combining_packets.append(('TR', responses))

      return self.format_packets(combining_packets)

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
      connection_packet = {
         'authority_ps' : 1,
         'ms' : request.msID,
         'time_range': request.start
      }

      #schedule the time end event
      request.eventID = self.scheduler.enterabs(request.end, 1, self.control_gs_end, (request))

      return ("gs", connection_packet)

   def control_gs_end(self, request):
      # TODO remove this completed time request from schedules
      pass

   def fwd_cancel(self, cancel_packets):
      return {cancel_packets['msID']: cancel_packets}

   def handle_response(self, response_packet):
      return ('fwd', response_packet)

   def ms_init(self, data):
      ms = MissionServer(data["name"], data["msID"])

      #check if ms is already in set
      if ms in self.ms_set:
         #TODO dont add it if already there?
         pass
      else:
         self.ms_set.add(ms)

      gs_list = {}
      gs_list[data['msID']] = {
         "type":"GS",
         "gsList":build_gs_array(self.gs_set)
      }

      return gs_list

   def ps_init(self, data):
      ps = PolicySever(data["name"], data["msID"])

      #check if ms is already in set
      if ps in self.ps_set:
         pass
      else:
         self.ps_set.add(ps)
