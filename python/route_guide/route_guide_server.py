# Copyright 2015, Google Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
#     * Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above
# copyright notice, this list of conditions and the following disclaimer
# in the documentation and/or other materials provided with the
# distribution.
#     * Neither the name of Google Inc. nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""The Python implementation of the gRPC route guide server."""

import json
import time
import math

import route_guide_pb2

_ONE_DAY_IN_SECONDS = 60 * 60 * 24


def read_route_guide_db():
  """Reads the route guide"""
  feature_list = []
  with open("route_guide_db.json") as route_guide_db_file:
    for item in json.load(route_guide_db_file):
      feature = route_guide_pb2.Feature(name=item["name"])
      feature.location.longitude = item["location"]["longitude"]
      feature.location.latitude = item["location"]["latitude"]
      feature_list.append(feature)
  return feature_list


def get_feature(feature_db, point):
  """Returns feature at given location or None"""
  for feature in feature_db:
    if feature.location == point:
      return feature
  return None


def get_distance(start, end):
  """Distance between two points"""
  coord_factor = 10000000.0
  lat_1 = start.latitude / coord_factor
  lat_2 = end.latitude / coord_factor
  lon_1 = start.latitude / coord_factor
  lon_2 = end.longitude / coord_factor
  lat_rad_1 = math.radians(lat_1)
  lat_rad_2 = math.radians(lat_2)
  delta_lat_rad = math.radians(lat_2 - lat_1)
  delta_lon_rad = math.radians(lon_2 - lon_1)

  a = pow(math.sin(delta_lat_rad / 2), 2) + math.cos(lat_rad_1) * math.cos(lat_rad_2) * pow(math.sin(delta_lon_rad / 2), 2)
  c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
  R = 6371000; # metres
  return R * c;

class RouteGuideServicer(route_guide_pb2.EarlyAdopterRouteGuideServicer):
  """Provides methods that implement functionality of route guide server."""

  def __init__(self):
    self.db = read_route_guide_db()

  def GetFeature(self, request, context):
    feature = get_feature(self.db, request)
    if not feature:
      feature = route_guide_pb2.Feature(name="")
      feature.location.longitude = request.longitude
      feature.location.latitude = request.latitude
    return feature

  def ListFeatures(self, request, context):
    lo = request.lo
    hi = request.hi
    left = min(lo.longitude, hi.longitude)
    right = max(lo.longitude, hi.longitude)
    top = max(lo.latitude, hi.latitude)
    bottom = min(lo.latitude, hi.latitude)
    for feature in self.db:
      if (feature.location.longitude >= left and
          feature.location.longitude <= right and
          feature.location.latitude >= bottom and
          feature.location.latitude <= top):
        yield feature

  def RecordRoute(self, request_iterator, context):
    point_count = 0
    feature_count = 0
    distance = 0.0
    prev_point = None

    start_time = time.time()
    for point in request_iterator:
      point_count += 1
      if get_feature(self.db, point):
        feature_count += 1
      if prev_point:
        distance += get_distance(prev_point, point)
      prev_point = point

    elapsed_time = time.time() - start_time
    return route_guide_pb2.RouteSummary(point_count=point_count,
                                        feature_count=feature_count,
                                        distance=int(distance),
                                        elapsed_time=int(elapsed_time))

  def RouteChat(self, request_iterator, context):
    prev_notes = []
    for new_note in request_iterator:
      for prev_note in prev_notes:
        if prev_note.location == new_note.location:
          yield prev_note
      prev_notes.append(new_note)


def serve():
  server = route_guide_pb2.early_adopter_create_RouteGuide_server(
      RouteGuideServicer(), 50051, None, None)
  server.start()
  try:
    while True:
      time.sleep(_ONE_DAY_IN_SECONDS)
  except KeyboardInterrupt:
    server.stop()

if __name__ == '__main__':
  serve()