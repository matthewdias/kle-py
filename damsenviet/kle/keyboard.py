from __future__ import annotations
from typing import (
    cast,
    Any,
    Union,
    Tuple,
    List,
    Dict,
)
from copy import deepcopy
from mpmath import mpf
from typeguard import typechecked
from .metadata import Metadata
from .background import Background
from .key import Key
from .exceptions import DeserializeException
from .utils import (
    T,
    S,
    autorepr,
    with_precision,
    kle_precision,
)

__all__ = ["Keyboard"]


Keyboard_JSON = List[Union[Dict, List[Union[str, Dict]]]]

# fmt: off
label_map = [
    # -1 indicates not used
    [0, 6, 2, 8, 9, 11, 3, 5, 1, 4, 7, 10],  # 0 = no centering
    [1, 7, -1, -1, 9, 11, 4, -1, -1, -1, -1, 10],  # 1 = center x
    [3, -1, 5, -1, 9, 11, -1, -1, 4, -1, -1, 10],  # 2 = center y
    [4, -1, -1, -1, 9, 11, -1, -1, -1, -1, -1, 10],  # 3 = center x & y
    [0, 6, 2, 8, 10, -1, 3, 5, 1, 4, 7, -1],  # 4 = center front (default)
    [1, 7, -1, -1, 10, -1, 4, -1, -1, -1, -1, -1],  # 5 = center front & x
    [3, -1, 5, -1, 10, -1, -1, -1, 4, -1, -1, -1],  # 6 = center front & y
    # 7 = center front & x & y
    [4, -1, -1, -1, 10, -1, -1, -1, -1, -1, -1, -1],
]


disallowed_alignnment_for_labels = [
    [1, 2, 3, 5, 6, 7],  # 0
    [2, 3, 6, 7],  # 1
    [1, 2, 3, 5, 6, 7],  # 2
    [1, 3, 5, 7],  # 3
    [],  # 4
    [1, 3, 5, 7],  # 5
    [1, 2, 3, 5, 6, 7],  # 6
    [2, 3, 6, 7],  # 7
    [1, 2, 3, 5, 6, 7],  # 8
    [4, 5, 6, 7],  # 9
    [],  # 10
    [4, 5, 6, 7]  # 11
]
# fmt: on


@typechecked
def unaligned(aligned_items: List, alignment: int, default_val: Any) -> List:
    """Returns the unaligned ordering of aligned items.

    :param items: The aligned_items to be unaligned.
    :type items: List
    :param align: The alignment option. 0-7
    :type align: int
    :return: The reordered items.
    :rtype: list
    """
    unaligned_items = [default_val for i in range(12)]
    for i, aligned_item in enumerate(aligned_items):
        unaligned_items[label_map[alignment][i]] = aligned_item
    return unaligned_items


@typechecked
def compare_text_sizes(
    text_sizes: Union[int, float, List[Union[int, float]]],
    aligned_text_sizes: List[Union[int, float]],
    aligned_text_labels: List[str],
) -> bool:
    """Determines whether text sizes and ordered version are equal.

    :param text_sizes: the text sizes to compare
    :type text_sizes: Union[int, List[int]]
    :param aligned_text_sizes: the ordered text sizes
    :type algined_text_sizes: List[Union[int, float]]
    :param aligned_text_labels: the ordered labels
    :type aligned_text_labels: List[str]
    :return: whether text sizes are equal
    :rtype: bool
    """
    if type(text_sizes) is int or type(text_sizes) is float:
        text_sizes = [text_sizes] + [0 for i in range(11)]
    for i in range(12):
        if aligned_text_labels[i] == "":
            continue

        if (
            # text size is non 0 and aligned text size is 0 or
            # text is 0 and aligned text size is non 0
            (bool(text_sizes[i]) != bool(aligned_text_sizes[i]))
            or (text_sizes[i] != 0 and text_sizes[i] != aligned_text_sizes[i])
        ):
            return False
    return True


@typechecked
def playback_metadata_changes(metadata: Metadata, metadata_changes: Dict) -> None:
    """Playback the changes into the metadata.

    :param metadata: metadata
    :type metadata: Metadata
    :param metadata_changes: the changes
    :type metadata_changes: Dict
    :return: the metadata
    :rtype: Metadata
    """
    if "author" in metadata_changes:
        metadata.author = metadata_changes["author"]
    if "backcolor" in metadata_changes:
        metadata.background_color = metadata_changes["backcolor"]
    if "background" in metadata_changes:
        if "name" in metadata_changes["background"]:
            metadata.background.name = metadata_changes["background"]["name"]
        if "style" in metadata_changes["background"]:
            metadata.background.style = metadata_changes["background"]["style"]
    if "name" in metadata_changes:
        metadata.name = metadata_changes["name"]
    if "notes" in metadata_changes:
        metadata.notes = metadata_changes["notes"]
    if "radii" in metadata_changes:
        metadata.radii = metadata_changes["radii"]
    if "switchMount" in metadata_changes:
        metadata.switch.mount = metadata_changes["switchMount"]
    if "switchBrand" in metadata_changes:
        metadata.switch.brand = metadata_changes["switchBrand"]
    if "switchType" in metadata_changes:
        metadata.switch.type = metadata_changes["switchType"]
    if "css" in metadata_changes:
        metadata.css = metadata_changes["css"]
    if "pcb" in metadata_changes:
        metadata.is_switches_pcb_mounted = metadata_changes["pcb"]
        metadata.include_switches_pcb_mounted = True
    if "plate" in metadata_changes:
        metadata.is_switches_plate_mounted = metadata_changes["plate"]
        metadata.include_switches_plate_mounted = True


@typechecked
def playback_key_changes(
    key: Key,
    key_changes: Dict,
    current_labels_color: List[str],
    current_labels_size: List[Union[int, float]],
    alignment: int,
    cluster_rotation_x: mpf,
    cluster_rotation_y: mpf,
) -> Tuple[List[str], List[Union[int, float]], int, mpf, mpf]:
    """Playback the changes into the key.

    :param key: the recording key
    :type key: Key
    :param key_changes: the changes
    :type key_changes: Dict
    :param current_labels_color: key's labels' color, default values set to ""
    :type current_labels_color: List[str]
    :param current_labels_size: key's labels' size, defaults values set to 0
    :type current_labels_size: List[Union[int, float]]
    :param alignment: the tracked text alignment
    :type alignment: int
    :param cluster_rotation_x: the tracked rotation origin x
    :type cluster_rotation_x: mpf
    :param cluster_rotation_y: the tracked rotation origin y
    :type cluster_rotation_y: mpf
    :return: current_labels_color, current_labels_size, align, cluster_rotation_x, cluster_rotation_y
    :rtype: Tuple[List[str], List[Union[int, float]], int, mpf, mpf]
    """
    if "r" in key_changes:
        key.rotation_angle = mpf(str(key_changes["r"]))
    if "rx" in key_changes:
        key.rotation_x = mpf(str(key_changes["rx"]))
        cluster_rotation_x = mpf(str(key_changes["rx"]))
        key.x = cluster_rotation_x
        key.y = cluster_rotation_y
    if "ry" in key_changes:
        key.rotation_y = mpf(str(key_changes["ry"]))
        cluster_rotation_y = mpf(str(key_changes["ry"]))
        key.x = cluster_rotation_x
        key.y = cluster_rotation_y
    if "a" in key_changes:
        alignment = key_changes["a"]
    if "f" in key_changes:
        key.default_text_size = key_changes["f"]
        for i in range(len([size for size in current_labels_size])):
            current_labels_size[i] = 0
    if "f2" in key_changes:
        for i in range(1, 12):
            current_labels_size[i] = key_changes["f2"]
    if "fa" in key_changes:
        for i in range(len(key_changes["fa"])):
            current_labels_size[i] = key_changes["fa"][i]
        for i in range(len(key_changes["fa"]), 12):
            current_labels_size[i] = 0
    if "p" in key_changes:
        key.profile_and_row = key_changes["p"]
    if "c" in key_changes:
        key.color = key_changes["c"]
    if "t" in key_changes:
        labels_color = deepcopy(key_changes["t"]).split("\n")
        if labels_color[0] != "":
            key.default_text_color = labels_color[0]
        for i, color in enumerate(unaligned(labels_color, alignment, "")):
            current_labels_color[i] = color
    if "x" in key_changes:
        key.x = key.x + mpf(str(key_changes["x"]))
    if "y" in key_changes:
        key.y = key.y + mpf(str(key_changes["y"]))
    if "w" in key_changes:
        key.width = mpf(str(key_changes["w"]))
        key.width2 = mpf(str(key_changes["w"]))
    if "h" in key_changes:
        key.height = mpf(str(key_changes["h"]))
        key.height2 = mpf(str(key_changes["h"]))
    if "x2" in key_changes:
        key.x2 = mpf(str(key_changes["x2"]))
    if "y2" in key_changes:
        key.y2 = mpf(str(key_changes["y2"]))
    if "w2" in key_changes:
        key.width2 = mpf(str(key_changes["w2"]))
    if "h2" in key_changes:
        key.height2 = mpf(str(key_changes["h2"]))
    if "n" in key_changes:
        key.is_homing = key_changes["n"]
    if "l" in key_changes:
        key.is_stepped = key_changes["l"]
    if "d" in key_changes:
        key.is_decal = key_changes["d"]
    if "g" in key_changes:
        key.is_ghosted = key_changes["g"]
    if "sm" in key_changes:
        key.switch.mount = key_changes["sm"]
    if "sb" in key_changes:
        key.switch.mount = key_changes["sb"]
    if "st" in key_changes:
        key.switch.mount = key_changes["st"]
    return (
        current_labels_color,
        current_labels_size,
        alignment,
        cluster_rotation_x,
        cluster_rotation_y,
    )


@typechecked
def key_sort_criteria(
    key: Key,
) -> Tuple[mpf, mpf, mpf, mpf, mpf]:
    """A helper to sort keys into the KLE order before serialization.

    :param key: the key to compare
    :type key: Key
    :return: the multidimensional ordering for comparison
    :rtype: Tuple[ mpf, mpf, mpf, mpf, mpf, ]
    """
    return (
        (key.rotation_angle + 360) % 360,
        key.rotation_x,
        key.rotation_y,
        key.y,
        key.x,
    )


@typechecked
def record_change(changes: Dict, name: str, val: T, default_val: S) -> T:
    """Registers the change if value is not equal to default.

    :param changes: the existing changes
    :type changes: Dict
    :param name: the property name
    :type name: str
    :param val: the value
    :type val: T
    :param default_val: the value to compare against
    :type default_val: T
    :return: the value
    :rtype: T
    """
    if val != default_val:
        if type(val) is mpf:
            # determine if you can use an in there
            if val % mpf(str(1.0)) == mpf(str(0.0)):
                changes[name] = int(val)
            else:
                changes[name] = float(val)
        else:
            changes[name] = val
    return val


@typechecked
def _reduced_text_sizes(text_sizes: List[Union[int, float]]):
    """Returns a copy of text sizes with right zeroes stripped.

    :param arr: [description]
    :type arr: List[Union[int, float]]
    :return: [description]
    :rtype: [type]
    """
    text_sizes: List[Union[int, float]] = deepcopy(text_sizes)
    while len(text_sizes) > 0 and text_sizes[-1] == 0:
        text_sizes.pop()
    return text_sizes


@typechecked
def _aligned_key_properties(
    key: Key,
    current_labels_size: List[Union[int, float]],
) -> Tuple[int, List[str], List[str], List[Union[int, float]]]:
    """More space efficient text labels, text colors, text sizes.

    :param key: the key to compute the reorder of
    :type key: Key
    :param current: the current key to compare to
    :type current: Key
    :return: a return dict with reordered version of props stored
    :rtype: Dict
    """
    # size and colors if match default changed to base values
    key_labels_size = [label.size for label in key.labels]
    key_labels_color = [label.color for label in key.labels]
    for i, label in enumerate(key.labels):
        if label.text == "":
            key_labels_color[i] = ""
            key_labels_size[i] = 0
        if label.color == key.default_text_color:
            key_labels_color[i] = ""
        if label.size == key.default_text_size:
            key_labels_size[i] = 0

    texts: List[str] = [label.text for label in key.labels]
    colors: List[str] = [color for color in key_labels_color]
    sizes: List[Union[int, float]] = [size for size in key_labels_size]
    alignments: List[int] = [7, 5, 6, 4, 3, 1, 2, 0]

    # remove impossible flag combinations
    for i in range(len(texts)):
        if texts[i] != "":
            try:
                for alignment in deepcopy(alignments):
                    if alignment in disallowed_alignnment_for_labels[i]:
                        alignments.remove(alignment)
            except ValueError:
                pass

    # generate label arrays in correct order
    alignment = alignments[0]
    aligned_text_labels = ["" for i in range(12)]
    aligned_text_color = ["" for i in range(12)]
    aligned_text_size = [0 for i in range(12)]
    for i in range(12):
        if i not in label_map[alignment]:
            continue
        ndx = label_map[alignment].index(i)
        if ndx >= 0:
            if texts[i] != "":
                aligned_text_labels[ndx] = texts[i]
            if colors[i] != "":
                aligned_text_color[ndx] = colors[i]
            if sizes[i] != 0:
                aligned_text_size[ndx] = sizes[i]
    # clean up
    for i in range(len(_reduced_text_sizes(aligned_text_size))):
        if aligned_text_labels[i] == "":
            aligned_text_size[i] = current_labels_size[i]
        if aligned_text_size == key.default_text_size:
            aligned_text_size[i] = 0

    return (
        alignment,
        aligned_text_labels,
        aligned_text_color,
        aligned_text_size,
    )


class Keyboard:
    """Class storing Keyboard."""

    def __init__(self, metadata: Metadata = None, keys: List[Key] = None):
        self.metadata: Metadata = Metadata()
        self.keys: List[Key] = []

    def __str__(self) -> str:
        return repr(self)

    def __repr__(self) -> str:
        return autorepr(
            self,
            {
                "metadata": self.metadata,
                "keys": self.keys,
            },
        )

    @property
    def metadata(self) -> Metadata:
        """Gets metadata.

        :return: metadata reference
        :rtype: Metadata
        """
        return self.__metadata

    @metadata.setter
    @typechecked
    def metadata(self, metadata: Metadata) -> None:
        """Sets metadata.

        :param metadata: metadata reference
        :type metadata: Metadata
        """
        self.__metadata = metadata

    @property
    @typechecked
    def keys(self) -> List[Key]:
        """Gets key references.

        :return: list of Key references
        :rtype: List[Key]
        """
        return self.__keys

    @keys.setter
    @typechecked
    def keys(self, keys: List[Key]) -> None:
        """Sets keys references.

        :param keys: list of Key references
        :type keys: List[Key]
        """
        self.__keys = keys

    @classmethod
    @with_precision(kle_precision)
    def from_json(
        cls,
        keyboard_json: Keyboard_JSON,
        normalize: bool = False,
    ) -> Keyboard:
        """Deserializes a KLE json array into a keyboard.

        :param keyboard_json: the KLE formatted json
        :type keyboard_json: List[Union[Dict, List[Union[str, Dict]]]]
        :param normalize: whether to normalize invalid values, silences errors when True
        :type normalize: bool
        :raises DeserializeException: keyboard_json is not an array
        :raises DeserializeException: rotation changes not at beginning of row
        :raises DeserializeException: metadata specified but not as first item
        :raises DeserializeException: item not expected type
        :return: the Keyboard
        :rtype: Keyboard
        """
        if type(keyboard_json) != list:
            raise DeserializeException(
                message="Expected an array of objects:",
                payload=keyboard_json,
            )

        keyboard: Keyboard = Keyboard()

        # tracks the key with accumulated changes
        current: Key = Key()
        # allows for non-KLE defaults for label initializer
        current_labels_size = [0 for label in current.labels]
        current_labels_color = ["" for label in current.labels]
        # tmp variables to construct final labels
        alignment: int = 4
        # keys are row separated by clusters
        # track rotation info for reset x/y positions
        cluster_rotation_x: mpf = mpf(str(0.0))
        cluster_rotation_y: mpf = mpf(str(0.0))

        # for object in list
        for r in range(len(keyboard_json)):
            if type(keyboard_json[r]) is list:
                # for item in list
                for k in range(len(keyboard_json[r])):
                    item: Union[str, dict] = cast(
                        Union[str, dict],
                        keyboard_json[r][k],
                    )
                    if type(item) is str:
                        labels: str = item
                        # create copy of key data
                        new_key: Key = deepcopy(current)
                        if new_key.width2 != 0:
                            new_key.width2 = current.width2
                        else:
                            new_key.width2 = current.width
                        if new_key.height2 != 0:
                            new_key.height2 = current.height2
                        else:
                            new_key.height2 = current.height
                        for i, text in enumerate(
                            unaligned(
                                labels.split("\n"),
                                alignment,
                                "",
                            )
                        ):
                            new_key.labels[i].text = text

                        for i, size in enumerate(
                            unaligned(
                                current_labels_size,
                                alignment,
                                0,
                            )
                        ):
                            if size == 0:
                                new_key.labels[i].size = new_key.default_text_size
                            else:
                                new_key.labels[i].size = size

                        for i, color in enumerate(current_labels_color):
                            if color == "":
                                new_key.labels[i].color = new_key.default_text_color
                            else:
                                new_key.labels[i].color = color

                        # add key
                        keyboard.keys.append(new_key)

                        # adjustments for the next key
                        current.x = current.x + mpf(current.width)
                        current.width = mpf(str(1.0))
                        current.height = mpf(str(1.0))
                        current.x2 = mpf(str(0.0))
                        current.y2 = mpf(str(0.0))
                        current.width2 = mpf(str(0.0))
                        current.height2 = mpf(str(0.0))
                        current.is_homing = False
                        current.is_stepped = False
                        current.is_decal = False

                    elif type(item) is dict:
                        key_changes = item
                        if k != 0 and (
                            "r" in key_changes
                            or "rx" in key_changes
                            or "ry" in key_changes
                        ):
                            message = (
                                "rotataion changes can only be made at the"
                                + "beginning of the row"
                            )
                            raise DeserializeException(
                                message=message,
                                payload=keyboard_json[r],
                            )
                        # rotation changes can only be specified at beginning
                        # at the start of the row
                        (
                            current_labels_color,
                            current_labels_size,
                            alignment,
                            cluster_rotation_x,
                            cluster_rotation_y,
                        ) = playback_key_changes(
                            current,
                            key_changes,
                            current_labels_color,
                            current_labels_size,
                            alignment,
                            cluster_rotation_x,
                            cluster_rotation_y,
                        )
                    else:
                        message = (
                            "expected an object specifying key changes or"
                            "text labels for a key"
                        )
                        raise DeserializeException(
                            message=message,
                            payload=item,
                        )
                current.y = current.y + mpf(str(1.0))
            elif type(keyboard_json[r]) is dict:
                metadata_changes = keyboard_json[r]
                if r != 0:
                    raise DeserializeException(
                        "metadata can only be specified as first item",
                        keyboard_json[r],
                    )
                playback_metadata_changes(keyboard.metadata, metadata_changes)
            else:
                message = (
                    "encountered unexpected type of "
                    f"{type(keyboard_json[r]).__name__}"
                )
                raise DeserializeException(message=message, payload=keyboard_json[r])
            current.x = mpf(str(current.rotation_x))
        return keyboard

    @with_precision(kle_precision)
    def to_json(self) -> Keyboard_JSON:
        """Serializes the Keyboard to a KLE formatted json.

        :param keyboard: the keyboard to deserialize
        :type keyboard: Keyboard
        :return: the KLE formatted json
        :rtype: List[Union[Dict, List[Union[str, Dict]]]]
        """
        keyboard_json: Keyboard_JSON = list()
        row: List[Union[str, Dict]] = list()
        current: Key = Key()
        align: int = 4
        current_labels_color: List[str] = current.default_text_color
        # allows for non-KLE defaults for label initializer, can maintain value invariants
        current_labels_size: List[Union[int, float]] = [0 for label in current.labels]
        cluster_rotation_angle: mpf = mpf(str(0.0))
        cluster_rotation_x: mpf = mpf(str(0.0))
        cluster_rotation_y: mpf = mpf(str(0.0))

        metadata_changes: Dict = dict()
        default_metadata: Metadata = Metadata()
        record_change(
            metadata_changes,
            "backcolor",
            self.metadata.background_color,
            default_metadata.background_color,
        )
        record_change(
            metadata_changes,
            "name",
            self.metadata.name,
            default_metadata.name,
        )
        record_change(
            metadata_changes,
            "author",
            self.metadata.author,
            default_metadata.author,
        )
        record_change(
            metadata_changes,
            "notes",
            self.metadata.notes,
            default_metadata.notes,
        )
        background_changes: Dict = dict()
        default_background: Background = Background()
        record_change(
            background_changes,
            "name",
            self.metadata.background.name,
            default_background.name,
        )
        record_change(
            background_changes,
            "style",
            self.__metadata.background.style,
            default_background.style,
        )
        if len(background_changes) > 0:
            record_change(metadata_changes, "background", background_changes, None)
        record_change(
            metadata_changes,
            "radii",
            self.metadata.radii,
            default_metadata.radii,
        )
        record_change(
            metadata_changes,
            "switchMount",
            self.metadata.switch.mount,
            default_metadata.switch.mount,
        )
        record_change(
            metadata_changes,
            "switchBrand",
            self.metadata.switch.brand,
            default_metadata.switch.brand,
        )
        record_change(
            metadata_changes,
            "switchType",
            self.metadata.switch.type,
            default_metadata.switch.type,
        )
        record_change(
            metadata_changes,
            "css",
            self.metadata.css,
            default_metadata.css,
        )
        if self.metadata.include_switches_plate_mounted or (
            self.metadata.is_switches_plate_mounted
            != default_metadata.is_switches_plate_mounted
        ):
            record_change(
                metadata_changes,
                "plate",
                self.metadata.is_switches_plate_mounted,
                None,
            )
        if self.metadata.include_switches_pcb_mounted or (
            self.metadata.is_switches_pcb_mounted
            != default_metadata.is_switches_pcb_mounted
        ):
            record_change(
                metadata_changes,
                "pcb",
                self.metadata.is_switches_pcb_mounted,
                None,
            )
        if len(metadata_changes) > 0:
            keyboard_json.append(metadata_changes)

        is_new_row: bool = True
        # will be incremented on first row
        current.y = current.y - mpf(str(1.0))

        sorted_keys: List[Key] = list(sorted(self.__keys, key=key_sort_criteria))
        for key in sorted_keys:
            key_changes = dict()
            (
                alignment,
                aligned_text_labels,
                aligned_text_color,
                aligned_text_size,
            ) = _aligned_key_properties(
                key,
                current_labels_size,
            )

            # start a new row when necessary
            is_cluster_changed: bool = (
                (key.rotation_angle != cluster_rotation_angle)
                or (key.rotation_x != cluster_rotation_x)
                or (key.rotation_y != cluster_rotation_y)
            )
            is_row_changed: bool = key.y != current.y
            if len(row) > 0 and (is_row_changed or is_cluster_changed):
                # set up for the new row
                keyboard_json.append(row)
                row = list()
                is_new_row = True

            if is_new_row:
                current.y = current.y + mpf(str(1.0))

                # set up for the new row
                # y is reset if either rx or ry are changed
                if (
                    key.rotation_y != cluster_rotation_y
                    or key.rotation_x != cluster_rotation_x
                ):
                    current.y = key.rotation_y
                # always reset x to rx (which defaults to zero)
                current.x = key.rotation_x

                # update current cluster
                cluster_rotation_angle = key.rotation_angle
                cluster_rotation_x = key.rotation_x
                cluster_rotation_y = key.rotation_y

                is_new_row = False

            current.rotation_angle = record_change(
                key_changes,
                "r",
                key.rotation_angle,
                current.rotation_angle,
            )
            current.rotation_x = record_change(
                key_changes,
                "rx",
                key.rotation_x,
                current.rotation_x,
            )
            current.rotation_y = record_change(
                key_changes,
                "ry",
                key.rotation_y,
                current.rotation_y,
            )
            current.y = current.y + record_change(
                key_changes,
                "y",
                key.y - current.y,
                mpf(str(0.0)),
            )
            current.x = (
                current.x
                + record_change(
                    key_changes,
                    "x",
                    key.x - current.x,
                    mpf(str(0.0)),
                )
                + key.width
            )
            current.color = record_change(
                key_changes,
                "c",
                key.color,
                current.color,
            )
            # if statement for ordered color
            if not aligned_text_color[0]:
                aligned_text_color[0] = key.default_text_color
            else:
                for i in range(2, 12):
                    if (
                        aligned_text_color[i] != ""
                        and aligned_text_color[i] != aligned_text_color[0]
                    ):
                        aligned_text_color[i] = key.default_text_color
            current_labels_color = record_change(
                key_changes,
                "t",
                "\n".join(aligned_text_color).rstrip(),
                current_labels_color,
            )
            current.is_ghosted = record_change(
                key_changes,
                "g",
                key.is_ghosted,
                current.is_ghosted,
            )
            current.profile_and_row = record_change(
                key_changes,
                "p",
                key.profile_and_row,
                current.profile_and_row,
            )
            current.switch.mount = record_change(
                key_changes,
                "sm",
                key.switch.mount,
                current.switch.mount,
            )
            current.switch.brand = record_change(
                key_changes,
                "sb",
                key.switch.brand,
                current.switch.brand,
            )
            current.switch.type = record_change(
                key_changes,
                "st",
                key.switch.type,
                current.switch.type,
            )
            align = record_change(
                key_changes,
                "a",
                alignment,
                align,
            )
            current.default_text_size = record_change(
                key_changes,
                "f",
                key.default_text_size,
                current.default_text_size,
            )
            if "f" in key_changes:
                current_labels_size = [0 for i in range(12)]
            # if text sizes arent already optimized, optimize it
            if not compare_text_sizes(
                current_labels_size, aligned_text_size, aligned_text_labels
            ):
                if len(_reduced_text_sizes(aligned_text_size)) == 0:
                    # force f to be written
                    record_change(
                        key_changes,
                        "f",
                        key.default_text_size,
                        -1,
                    )
                else:
                    optimizeF2: bool = not bool(aligned_text_size[0])
                    for i in range(2, len(_reduced_text_sizes(aligned_text_size))):
                        if not optimizeF2:
                            break
                        optimizeF2 = aligned_text_size[i] == aligned_text_size[1]
                    if optimizeF2:
                        f2: Union[int, float] = aligned_text_size[1]
                        # current.f2 not ever used
                        # removed current.f2 = serializeProp(props, "f2", f2, -1);
                        record_change(key_changes, "f2", f2, -1)
                        current_labels_size = [0] + [f2 for i in range(11)]
                    else:
                        current_labels_size = aligned_text_size
                        record_change(
                            key_changes,
                            "fa",
                            _reduced_text_sizes(aligned_text_size),
                            [],
                        )
            record_change(key_changes, "w", key.width, mpf(str(1.0)))
            record_change(key_changes, "h", key.height, mpf(str(1.0)))
            record_change(key_changes, "w2", key.width2, key.width)
            record_change(key_changes, "h2", key.height2, key.height)
            record_change(key_changes, "x2", key.x2, mpf(str(0.0)))
            record_change(key_changes, "y2", key.y2, mpf(str(0.0)))
            record_change(key_changes, "n", key.is_homing, False)
            record_change(key_changes, "l", key.is_stepped, False)
            record_change(key_changes, "d", key.is_decal, False)
            if len(key_changes) > 0:
                row.append(key_changes)
            row.append("\n".join(aligned_text_labels).rstrip())
        if len(row) > 0:
            keyboard_json.append(row)
        return keyboard_json
