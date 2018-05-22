import json

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

def relay_stripped_groundstation_metadata(self, groundstation_metadata):
   """
   Event: on recieve of our own ground station metadata packet

   Strips the groundstation metadata into information other mission servers
   require in order to make a decision what groundstations it wants. (We don't
   want to share all of our groundstations data, just what's necessary). Then
   it relays this stripped groundstationd data to all connected servers
   (policy and mission).

   Args:
      self: maybe a policy server is an obejct with a list/set/dict of all servers
         (mission and policy) it is connected to. We will need addresses of both
         for communication.

      metadata: the metadata we recieve from the groundstation

   Returns:
   """
   stripped_groundstation_metadata = strip_groundstation_metadata(groundstation_metadata)

   # Relay the groundstation schedule to all connected servers
   for mission_server in self.mission_servers:
      # For mission_serves, you can have a different strip function, since you might
      # be willing to share more data with you rown mission servers vs. other
      # policy servers
      self.connections[mission_server].send(stripped_groundstation_metadata)
   for policy_server in self.policy_servers:
      self.connections[policy_server].send(stripped_groundstation_metadata)

   return

def fwd_stripped_groundstation_metadata(self, stripped_groundstaiton_metadata):
   """
   Event: On receive of another school's stripped groundstation metadata packet
      from another school's server (policy)

   Forwards this groundstation metadata packet to its own servers (mission)

   Args:
      self: maybe a policy server is an object with a list/set/dict of all servers
         (mission and policy) it is connected to. We will need addresses of just
         the server (mission) for communication.

      stripped_data: a stripped metadata of some groundstation

   Returns:
   """

   # For each connected mission server (SELF)
      # Forward your recieved schedule from someone else's groundstation (GROUNDSTATION)


def fwd_groundsation_request(self, ground_station_request):
   """
   Event: On receive of a ground station request for another school's ground
      station from our own server (mission)

   Forwards this schedule to corresponding servers (policy)

   Args:
      self: maybe a policy server is an obejct with a list of all servers
      (mission and policy) it is connected to. We will need addresses of just
      the servers (policy) for communication.

      ground_station_request: A ground station request packet indicating what
         ground station a server (mission) wants scheduled time with

   Returns:
   """

   # tell Purdue's (or some school) policy server that I want this schedule

def sched_groundstation_request(self, ground_station_request):
   """
   Event: on recieve of requests for a server's (policy) our own groundstations

   Uses the comparator(or something) that the policy server uses to determine
   how much time the requesting server (mission) gets with the groundstation
   schedules that time into its own table, and relays the decision back to the
   policy server for which the requesting misison server is under.

   Args:
      groundstation_request: a groundstation request packet

   Returns:
   """

def control_groundstation(self):
   """
   Event: On recieve time notification from our groundstation_schedules

   Tells the groundstation to connect to the mission server for the time specified
   by our schedule

   Args:
      self:
         groundstation_schedule: the schedule

         groundstation: the groundstation related to the schedule. The ground
            station will initiate the request with the mission_Server specified

         mission_server_address: the mission server the the requested time, will
            will now get its time

   Returns: Nothing
   """