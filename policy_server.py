import json
from collections import defaultdict

class Schedule(object):
   """schedule object

   Attributes:
      gs_id (int): the id of the groundstation related to this schedule
      ms_id (int): the id of the mission server related to this schedule
      start (int): start time of schedule
      end (int): end time of the schedule
   """
   def __init__(self, req_packet):
      self.reqID = req_packet['reqID']
      self.gsID = req_packet['gsID']
      self.start = req_packet['start']
      self.end = req_packet['end']

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
      if self.gsID != sched.ms_id: return False

      ends_between = self.start <= sched.end and sched.end <= self.end
      starts_between = self.start <= sched.end and sched.end <= self.end
      starts_before_and_ends_after = sched.start <= self.start and self.end <= sched.end

      return ends_between or starts_between or starts_before_and_ends_after

def merge_dict_of_lists(d1, d2):
   """merges a dictionary that has a values of type list
      note: d1 must be a default dict type
   """
   for k, v in d2.items():
      d1[k] += v

class PS(object):
   """Contains all relevant logic and data necessary for gss

   Attributes:
      id (int): The id of the policy station

      schedules (schedule): set of schedules

      ms_set {int}: list of mission server ids connected to us

      gs_set {int}: list of groundstation ids connected to us
   """
   def __init__(self):
      self.id = 0
      self.schedules = set()
      self.ms_set = set()
      self.gs_set = set()

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

   def fwd_stripped_gs_metadata(self, stripped_gs_metadata):
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
      self.schedules.remove(gs_request['reqID'])

      return withdrawl_ack

   def has_priority(self, req_id_1, req_id_2):
      """ Given two mission server ids, return true if ms_id_1 has priority
      over ms_id_2, this implementation is left up to the school
      """
      # FOR NOW
      return req_id_1 > req_id_2

   def handle_schedule_request(self, gs_request):
      """tries to schedule a single request
      conflict --> nack
      conflict but has priority --> cancel to original schedule and ack
      no conflict --> ack
      """
      responses = defaultdict(list)
      cancels = defaultdict(list)

      # create a schedule object
      request = Schedule(gs_request)
      reqID = request.reqID

      conflicting_schedules = filter(request.has_conflict, self.schedules)

      # If we able to acquire conflicting schedules, we have a conflict
      if conflicting_schedules:
         lower_priority = lambda sched: self.has_priority(sched.reqID, request.reqID)
         lower_priority_scheds = filter(lower_priority, conflicting_schedules)

      # If we have a conflict, but have priority over all those conflicts
         if len(lower_priority_scheds) == len(conflicting_schedules):
            self.schedules.add(request)

            # add ack to dictionary of packets to be sent
            responses[reqID].append({'reqID': reqID, 'ack' : True, 'wd' : False})

            # add cancel packet to those conflicts we're overriding
            list_of_conflicting_scheds_as_dict = [x.__dict__ for x in conflicting_schedules]
            merge_dict_of_lists(cancels, self.handle_cancel(list_of_conflicting_scheds_as_dict))

      # Else, we have no conflict and we can just send an ack
      else:
         responses[reqID].append({'reqID': reqID, 'ack' : True, 'wd' : False})

      return responses, cancels

   def already_scheduled_with_own_gs(self, gs_request):
      """tells you if this gs_request has already been fulfilled by our own
      groundstations so that we can filter some requests for other gs before
      sending it out"""
      # isntantiate object just so we can use the method
      request = Schedule(gs_request)

      for schedule in self.schedules:
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
         for msg_type, packet_list in packet.items():
            packets[msg_type] = {'type': packet_type, list_name_mapping[packet_type]: packet_list}

      return packets

   def handle_requests(self, gs_requests):
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
            responses += self.handle_withdrawl(gs_request)
         else:
            some_responses, some_cancels = self.handle_schedule_request(gs_request)
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

      return self.format_packets([('RESP', responses),
                                  ('cancel', cancels),
                                  ('TR', fwd_filtered_requests_for_other_gs)])

   def control_gs(self, authority_ps, ms, time_range):
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

      connection_packet = {
         'authority_ps' : authority_ps,
         'ms' : ms,
         'time_range': time_range
      }

      return ("gs", connection_packet)

   def fwd_cancel(self, cancel_packets):
      return {cancel_packets['msID']: cancel_packets}

   def handle_cancel(self, cancel_packets):
      """does the requested cancels
      """
      cancel_forwards = defaultdict(list)
      for cancel_packet in cancel_packets:
         # Cancel the schedule by removing it from the policy servers schedule
         # But also get it so we can get the msID
         canceled_sched = self.schedules.pop([cancel_packet['reqID']])

         #Forward cancel to corresponding mission server
         msID = canceled_sched.msID
         reqID = canceled_sched.reqID
         cancel_forwards[msID].append({'reqID': reqID})

      return cancel_forwards

   def handle_response(self, response_packet):
      return ('fwd', response_packet)

   def init(self):
      # need to give groundstation a name
      pass