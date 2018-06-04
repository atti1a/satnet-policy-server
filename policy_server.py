import json

class policy_server(object):
   """Contains all relevant logic and data necessary for groundstations

   Attributes:
      id (int): The id of the policy station

      schedules (dict of groundstation_id: schedule object): list of schedules
      for each groundstation
   """
   def __init__(self):
      self.id = 0
      self.schedule = {}

   def strip_groundstation_metadata(groundstation_metadata):
      """
      Strips down groundstation metadata packet, because we don't actually want to
      broadcast all info just the info that's necessary for other mission servers
      to make its decision

      Args:
         groundstation_metadata: the metadata packet we recieve from the groundstation
            (JSON object)

      Returns: stripped down groundstation metadata (JSON file to be sent)
      """

      # create stripped down metadata
      stripped_metadata = {}
      required_fields_in_stripped_metadata = {
         'location',
         'authority_policy_server',
         'groundstation_id'
      }

      for required_field in required_fields_in_stripped_metadata:
         stripped_metadata[required_field] = groundstation_metadata[required_field]

      return json.dumps(stripped_metadata)

   def relay_stripped_groundstation_metadata(groundstation_metadata):
      """
      Event: on recieve of our own ground station metadata packet

      Strips the groundstation metadata into information other servers (mission)
      require in order to make a decision what groundstations it wants. (We don't
      want to share all of our groundstations data, just what's necessary). Then
      it relays this stripped groundstationd data to all connected servers
      (policy and mission).

      Args:
         groundstation_metadata: the metadata we recieve from the groundstation

      Returns: (destination, packet)
         destination: "servers" destination specifies that the packet will be sent
         to all connected servers (policy and mission) to our server (policy)

         packet: the stripped groundstation metadata is the packet that will be
         sent to all the servers (policy and mission)
      """
      stripped_groundstation_metadata = strip_groundstation_metadata(groundstation_metadata)

      return [("servers", stripped_groundstation_metadata)]

   def fwd_stripped_groundstation_metadata(stripped_groundstation_metadata):
      """
      Event: On receive of another school's stripped groundstation metadata packet
         from another school's server (policy)

      Forwards this groundstation metadata packet to its own servers (mission)

      Args:
         stripped_groundstation_metadata: a packet containing stripped metadata of
         some groundstation

      Returns: (destination, packet)
         destination: "mission_servers" destination specifies that the packet will
         be sent to all connected servers (mission) to our server (policy)

         packet: the stripped groundstation metadata is the packet containing useful
         metadata regarding a groundstation that will be sent to all the servers
         (policy and mission)
      """

      return [("mission_servers", stripped_groundstation_metadata)]

   def fwd_groundsation_request(ground_station_request):
      """
      Event: On receive of a ground_station request packet for another school's
         ground station from our own server (mission)

      Forwards this groundstation request packet to corresponding servers (policy)

      Args:
         self: maybe a policy server is an obejct with a list of all servers
         (mission and policy) it is connected to. We will need addresses of just
         the servers (policy) for communication.

         ground_station_request: A ground station request packet indicating what
            ground station a server (mission) wants scheduled time with (JSON obj)

      Returns:
      """

      return [("forward", ground_station_request)]

   def sched_groundstation_request(self, groundstation_id, schedule_request):
      """
      Event: on recieve of requests from another server's (policy) for our own
      groundstations

      Uses the comparator(or something) that the policy server uses to determine
      how much time the requesting server (mission) gets with the groundstation
      schedules that time into its own table, and relays the decision back to the
      policy server for which the requesting misison server is under. Also cancels
      another schedule if this request has a higher priority than the current
      scheduled slot. If a request has higher priority than all conflicting times
      then it will kick them all off, else it won't be schedule. (All or nothing)

      Args:
         curr_schedule:

      Returns:
      """
      # should i keep a local variable of curr_schedule
      schedulable, conflicting_schedules = schedule_time(curr_schedule, schedule_request)

      if schedulable:
         for conflicting_schedule in conflicting_schedules:
            #send cancel or something, how to handle this
         return "respond", ack_packet
      else:
         return "respond", nack_packet

         #return array of tuples

   def control_groundstation(authority_policy_server, mission_server, time_range):
      """
      Event: On recieve time notification from our groundstation_schedules

      Creates the packet that tells the groundstation to connect to the server
      (mission) for the time specified by our schedule

      Args:
         authority_policy_server: the server (policy) responsible for the server
         (mission) that the groundstation should connect to

         mission_server: the server (misison) that the groundstation should connect
         to

         time_range: the time range for which the ground station should be
         connected to the server (mission)

      Returns: tuple (destination, packet)
         destination: "groundstation" destination specifies a message towards the
         groundstation related to the event call

         packet: "connection_packet" the packet with necessary information for the
         ground station to connect to he corresponding server (mission)
      """

      connection_packet = json.dumps({
         'authority_policy_server' : authority_policy_server,
         'mission_server' : mission_server,
         'time_range': time_range
      })

      return "groundstation", connection_packet

   def cancel_schedule():
      #cancel ids will have the request in them
      #does the event create the packet? because it doesn't have access to the
      #sequence numeber, or
      #respond

   def handle_cancel(request_ID):
      """
      Event: On receive of a ground_station request packet for another school's
         ground station from our own server (mission)

      Forwards this groundstation request packet to corresponding servers (policy)

      Args:
         self: maybe a policy server is an obejct with a list of all servers
         (mission and policy) it is connected to. We will need addresses of just
         the servers (policy) for communication.

         ground_station_request: A ground station request packet indicating what
            ground station a server (mission) wants scheduled time with (JSON obj)

      Returns:
      """

      # tell Purdue's (or some school) policy server that I want this schedule
      #if authority_policy_server in self.policy_servers:
      #   self.authority_policy_server.send(ground_station_request)
      #else:
      #   print("ERROR: authority policy server is not in our list of servers")

      return "forward", ground_station_request

   def handle_response(request_ID, is_withdrawl):
      """
      Event: On receive of a ground_station request packet for another school's
         ground station from our own server (mission)

      Forwards this groundstation request packet to corresponding servers (policy)

      Args:
         self: maybe a policy server is an obejct with a list of all servers
         (mission and policy) it is connected to. We will need addresses of just
         the servers (policy) for communication.

         ground_station_request: A ground station request packet indicating what
            ground station a server (mission) wants scheduled time with (JSON obj)

      Returns:
      """

      # tell Purdue's (or some school) policy server that I want this schedule
      #if authority_policy_server in self.policy_servers:
      #   self.authority_policy_server.send(ground_station_request)
      #else:
      #   print("ERROR: authority policy server is not in our list of servers")

      return "forward", ground_station_request

   #region oldcode
   def request_comparator(requester1, requester2):
      school_priority = {
         'Cal Poly': 1,
         'Purdue': 2,
         'Berkeley': 3,
         'Stanford': 3,
      }

      return school_priority[requester1['school']] - school_priority[requester2['school']]

   def extract_request_source(self, ground_station_request):
      # what we will call it: the information we want to extract from packet
      relevant_fields = {
         'dest_policy_server': 'authority_policy_server',
         'dest_mission_server': 'mission_server',
         'groundstation': 'groundstation'
      }

      extracted_info = []

      # add our own fields
      extracted_info.append(
         {'authority_policy_server': self.id}
      )

      for name, relevant_field in relevant_fields.items():
         extracted_info.append(
            {name: ground_station_request[relevant_field]}
         )

      return extracted_info
   #endregion