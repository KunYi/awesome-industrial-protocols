# Turn/IP
# Claire-lex - 2023
# Packets and Packet class
# pylint: disable=invalid-name,no-member,too-many-instance-attributes
# pylint: disable=arguments-differ,too-many-arguments

"""Classes that represent and handle packets' info from the database.
"""

from config import packets as p, mongodb
from . import MongoDB, DBException, Collection, Document, Protocol, search

#-----------------------------------------------------------------------------#
# Constants                                                                   #
#-----------------------------------------------------------------------------#

ERR_EMPTY = "A packet must have at least a name and a protocol."
ERR_NOPACKET = "No packet found for protocol {0}."
ERR_UNKPACKET = "The packet '{0}' does not exists for protocol {1}."
ERR_EXIPACKET = "The packet '{0}' already exists for protocol {1}."
ERR_UNKFIELD = "Field '{0}' not found."
ERR_UNKID = "This ID does not match with any existing packet ({0})."

#-----------------------------------------------------------------------------#
# Packet class                                                                #
#-----------------------------------------------------------------------------#

class Packet(Document):
    """Class representing a single packet document."""
    protocol = None # Protocol document id in database
    description = None
    scapy_pkt = None
    raw_pkt = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = kwargs[p.name] if p.name in kwargs else None
        self.protocol = kwargs[p.protocol] if p.protocol in kwargs else None
        self.description = kwargs[p.description] if p.description in kwargs else None
        self.scapy_pkt = kwargs[p.scapy_pkt] if p.scapy_pkt in kwargs else None
        self.raw_pkt = kwargs[p.raw_pkt] if p.raw_pkt in kwargs else None
        self.fields_dict = {
            p.name: self.name,
            p.protocol: self.protocol,
            p.description: self.description,
            p.scapy_pkt: self.scapy_pkt,
            p.raw_pkt: self.raw_pkt
        }
        self.__check()

    def __str__(self):
        s = ["[{0}] {1}: {2}".format(self.protocol, self.name, self.description)]
        if self.scapy_pkt:
            s += ["\tScapy format: {0}".format(self.scapy_pkt)]
        if self.raw_pkt:
            s += ["\tRaw packet: {0}".format(self.raw_pkt)]
        return "\n".join(s)

    #--- Public --------------------------------------------------------------#

    def set(self, field: str, value: str) -> None:
        """Set value to field."""
        field = field.lower()
        if field not in self.fields_dict.keys():
            raise DBException(ERR_UNKFIELD.format(field))
        self.fields_dict[field] = value
        document = {p.name: self.name, p.protocol: self.protocol}
        newvalue = {field: value}
        self._db.packets.update_one(document, {"$set": newvalue})

    def check(self):
        self.__check()

    def to_dict(self, exclude_id: bool = True) -> dict:
        """Convert a packet object's content to dictionary."""
        pdict = {
            p.name: self.name,
            p.protocol: self.protocol,
            p.description: self.description,
            p.scapy_pkt: self.scapy_pkt,
            p.raw_pkt: self.raw_pkt
        }
        if not exclude_id:
            pdict[p.id] = self._id
        return pdict

    #--- Private -------------------------------------------------------------#

    def __check(self):
        if not self.name or not self.protocol:
            raise DBException(ERR_EMPTY)

#-----------------------------------------------------------------------------#
# Packets                                                                     #
#-----------------------------------------------------------------------------#

class Packets(Collection):
    """Interface with database to handle the packets' collection."""

    def __init__(self):
        super().__init__()

    def get(self, protocol: str, name: str = None) -> object:
        """Get a Packet object by its name and protocol.

        If the name of the packet is not set, return all the packets matching
        with protocol.
        """
        match = []
        for packet in self.all_as_objects:
            if search(protocol, packet.protocol):
                if not name:
                    match.append(packet)
                elif search(name, packet.name):
                    return packet
        if match:
            return match
        raise DBException(ERR_UNKPACKET.format(name, protocol) if name \
                          else ERR_NOPACKET.format(protocol))

    def get_id(self, iddb: object) -> Packet:
        """Get a packet object by its ID in database."""
        for packet in self.all:
            if packet[p.id] == iddb:
                return Packet(**packet)
        raise DBException(ERR_UNKID.format(iddb))

    def add(self, packet: Packet):
        """Add a packet to the collection."""
        try:
            self.get(packet.protocol, packet.name)
        except DBException:
            pass # The packet does not exist, we can continue
        else:
            raise DBException(ERR_EXIPACKET.format(packet.name, packet.protocol))
        self._db.packets.insert_one(packet.to_dict())

    def delete(self, protocol: Protocol, packet: Packet) -> None:
        """Delete an existing packet."""
        self.get(protocol, packet.name) # Will raise if unknown
        self._db.packets.delete_one({p.name: packet.name,
                                      p.protocol: protocol.name})

    @property
    def all(self) -> list:
        """Return the list of packets as JSON."""
        return self._db.packets_all

    @property
    def all_as_objects(self) -> list:
        """Return the list of packets as Packet objects."""
        objects = [Packet(**x) for x in self._db.packets_all]
        return sorted(objects, key=lambda x: x.protocol.lower())

    @property
    def count(self) -> int:
        """Return the total number of packets."""
        return self._db.packets_count
