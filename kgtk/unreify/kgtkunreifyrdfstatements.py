"""
This is a template for copying rows from an input KGTK file to an output
KGTK file.

"""
from argparse import ArgumentParser, Namespace
import attr
from pathlib import Path
import sys
import typing

from kgtk.kgtkformat import KgtkFormat
from kgtk.io.kgtkreader import KgtkReader, KgtkReaderMode, KgtkReaderOptions
from kgtk.io.kgtkwriter import KgtkWriter
from kgtk.unreify.kgtksortbuffer import KgtkSortBuffer
from kgtk.utils.argparsehelpers import optional_bool
from kgtk.value.kgtkvalueoptions import KgtkValueOptions

@attr.s(slots=True, frozen=False)
class KgtkUnreifyRdfStatements(KgtkFormat):
    DEFAULT_TRIGGER_LABEL_VALUE: str = "rdf:type"
    DEFAULT_TRIGGER_NODE2_VALUE: str = "rdf:Statement"
    DEFAULT_RDF_OBJECT_LABEL_VALUE: str = "rdf:object"
    DEFAULT_RDF_PREDICATE_LABEL_VALUE: str = "rdf:predicate"
    DEFAULT_RDF_SUBJECT_LABEL_VALUE: str = "rdf:subject"

    input_file_path: Path = attr.ib(validator=attr.validators.instance_of(Path))
    output_file_path: Path = attr.ib(validator=attr.validators.instance_of(Path))

    reified_file_path: typing.Optional[Path] = attr.ib(validator=attr.validators.optional(attr.validators.instance_of(Path)))
    unreified_file_path: typing.Optional[Path] = attr.ib(validator=attr.validators.optional(attr.validators.instance_of(Path)))
    uninvolved_file_path: typing.Optional[Path] = attr.ib(validator=attr.validators.optional(attr.validators.instance_of(Path)))

    trigger_label_value: str = attr.ib(validator=attr.validators.instance_of(str), default=DEFAULT_TRIGGER_LABEL_VALUE)
    trigger_node2_value: str = attr.ib(validator=attr.validators.instance_of(str), default=DEFAULT_TRIGGER_NODE2_VALUE)
    rdf_object_label_value: str = attr.ib(validator=attr.validators.instance_of(str), default=DEFAULT_RDF_OBJECT_LABEL_VALUE)
    rdf_predicate_label_value: str = attr.ib(validator=attr.validators.instance_of(str), default=DEFAULT_RDF_PREDICATE_LABEL_VALUE)
    rdf_subject_label_value: str = attr.ib(validator=attr.validators.instance_of(str), default=DEFAULT_RDF_SUBJECT_LABEL_VALUE)

    # TODO: find working validators
    # value_options: typing.Optional[KgtkValueOptions] = attr.ib(attr.validators.optional(attr.validators.instance_of(KgtkValueOptions)), default=None)
    reader_options: typing.Optional[KgtkReaderOptions]= attr.ib(default=None)
    value_options: typing.Optional[KgtkValueOptions] = attr.ib(default=None)

    error_file: typing.TextIO = attr.ib(default=sys.stderr)
    verbose: bool = attr.ib(validator=attr.validators.instance_of(bool), default=False)
    very_verbose: bool = attr.ib(validator=attr.validators.instance_of(bool), default=False)

    def process(self):
        # Open the input file.
        if self.verbose:
            print("Opening the input file: %s" % str(self.input_file_path), file=self.error_file, flush=True)

        kr: KgtkReader =  KgtkReader.open(self.input_file_path,
                                          mode=KgtkReaderMode.EDGE, # Must be an edge file.
                                          error_file=self.error_file,
                                          options=self.reader_options,
                                          value_options = self.value_options,
                                          verbose=self.verbose,
                                          very_verbose=self.very_verbose,
        )

        output_column_names: typing.List[str] = kr.column_names.copy()

        node1_column_idx: int = kr.node1_column_idx
        node1_column_name: str = output_column_names[node1_column_idx]

        label_column_idx: int = kr.label_column_idx
        label_column_name: str = output_column_names[label_column_idx]

        node2_column_idx: int = kr.node2_column_idx
        node2_column_name: str = output_column_names[node2_column_idx]

        # Adding an ID column?
        new_id_column: bool = False
        id_column_idx: int = kr.id_column_idx
        if id_column_idx < 0:
            new_id_column = True
            id_column_idx = len(output_column_names)
            output_column_names.append(KgtkFormat.ID)
        id_column_name: str = output_column_names[id_column_idx]

        if self.verbose:
            print("Opening the output file: %s" % str(self.output_file_path), file=self.error_file, flush=True)
        # Open the output file.
        kw: KgtkWriter = KgtkWriter.open(output_column_names,
                                         self.output_file_path,
                                         mode=KgtkWriter.Mode[kr.mode.name],
                                         require_all_columns=True,
                                         prohibit_extra_columns=True,
                                         fill_missing_columns=False,
                                         gzip_in_parallel=False,
                                         verbose=self.verbose,
                                         very_verbose=self.very_verbose)

        reifiedw: typing.Optional[KgtkWriter] = None
        if self.reified_file_path is not None:
            if self.verbose:
                print("Opening the reified RDF statements output file: %s" % str(self.reified_file_path), file=self.error_file, flush=True)
            reifiedw: KgtkWriter = KgtkWriter.open(kr.column_names,
                                                   self.reified_file_path,
                                                   mode=KgtkWriter.Mode[kr.mode.name],
                                                   require_all_columns=True,
                                                   prohibit_extra_columns=True,
                                                   fill_missing_columns=False,
                                                   gzip_in_parallel=False,
                                                   verbose=self.verbose,
                                                   very_verbose=self.very_verbose)

        unreifiedw: typing.Optional[KgtkWriter] = None
        if self.unreified_file_path is not None:
            if self.verbose:
                print("Opening the unreified RDF statements output file: %s" % str(self.unreified_file_path), file=self.error_file, flush=True)
            unreifiedw: KgtkWriter = KgtkWriter.open(output_column_names,
                                                   self.unreified_file_path,
                                                   mode=KgtkWriter.Mode[kr.mode.name],
                                                   require_all_columns=True,
                                                   prohibit_extra_columns=True,
                                                   fill_missing_columns=False,
                                                   gzip_in_parallel=False,
                                                   verbose=self.verbose,
                                                   very_verbose=self.very_verbose)

        uninvolvedw: typing.Optional[KgtkWriter] = None
        if self.uninvolved_file_path is not None:
            if self.verbose:
                print("Opening the uninvolved records output file: %s" % str(self.uninvolved_file_path), file=self.error_file, flush=True)
            uninvolvedw: KgtkWriter = KgtkWriter.open(kr.column_names,
                                                   self.uninvolved_file_path,
                                                   mode=KgtkWriter.Mode[kr.mode.name],
                                                   require_all_columns=True,
                                                   prohibit_extra_columns=True,
                                                   fill_missing_columns=False,
                                                   gzip_in_parallel=False,
                                                   verbose=self.verbose,
                                                   very_verbose=self.very_verbose)

        if self.verbose:
            print("Reading and grouping the input records.", file=self.error_file, flush=True)
        ksb: KgtkSortBuffer = KgtkSortBuffer.readall(kr, grouped=True, keygen=KgtkSortBuffer.node1_keygen)

        input_group_count: int = 0
        input_line_count: int = 0
        output_line_count: int = 0
        unreification_count: int = 0

        if self.verbose:
            print("Processing the input records.", file=self.error_file, flush=True)

        node1_group: typing.List[typing.List[str]]
        for node1_group in ksb.groupiterate():
            input_group_count += 1

            saw_trigger: bool = False
            node1_value: typing.Optional[str] = None
            rdf_object_value: typing.Optional[str] = None
            rdf_predicate_value: typing.Optional[str] = None
            rdf_subject_value: typing.Optional[str] = None
            
            potential_edge_attributes: typing.List[typing.List[str]] = [ ]

            row: typing.List[str]
            for row in node1_group:
                input_line_count += 1
                if node1_value is None:
                    node1_value = row[node1_column_idx]
                label: str = row[label_column_idx]
                node2: str = row[node2_column_idx]

                if label == self.trigger_label_value and node2 == self.trigger_node2_value:
                    if saw_trigger:
                        # TODO: Shout louder.
                        if self.verbose:
                            print("Warning: Duplicate trigger in input group %d (%s)" % (input_group_count, node1_value), file=self.error_file, flush=True)
                    saw_trigger = True
                elif label == self.rdf_object_label_value:
                    if rdf_object_value is not None and rdf_object_value != node2:
                        # TODO: Shout louder.
                        if self.verbose:
                            print("Warning: Multiple rdf objects in input group %d (%s)" % (input_group_count, node1_value), file=self.error_file, flush=True)
                    rdf_object_value = node2
                elif label == self.rdf_predicate_label_value:
                    if rdf_predicate_value is not None and rdf_predicate_value != node2:
                        # TODO: Shout louder.
                        if self.verbose:
                            print("Warning: Multiple rdf predicates in input group %d (%s)" % (input_group_count, node1_value), file=self.error_file, flush=True)
                    rdf_predicate_value = node2
                elif label == self.rdf_subject_label_value:
                    if rdf_subject_value is not None and rdf_subject_value != node2:
                        # TODO: Shout louder.
                        if self.verbose:
                            print("Warning: Multiple rdf subjects in input group %d (%s)" % (input_group_count, node1_value), file=self.error_file, flush=True)
                    rdf_subject_value = node2
                else:
                    potential_edge_attributes.append(row)
                    
            if saw_trigger and \
               node1_value is not None and \
               rdf_object_value is not None and \
               rdf_predicate_value is not None and \
               rdf_subject_value is not None:
                # Unreification was triggered.
                unreification_count += 1

                if reifiedw is not None:
                    for row in node1_group:
                        reifiedw.write(row)

                # Generate the new edge:
                kw.writemap({
                    node1_column_name: rdf_subject_value,
                    label_column_name: rdf_predicate_value,
                    node2_column_name: rdf_object_value,
                    id_column_name: node1_value,
                })
                output_line_count += 1

                if unreifiedw is not None:
                    unreifiedw.writemap({
                        node1_column_name: rdf_subject_value,
                        label_column_name: rdf_predicate_value,
                        node2_column_name: rdf_object_value,
                        id_column_name: node1_value,
                    })

                width: int = len(str(len(potential_edge_attributes)).strip())
                attribute_number: int = 0
                edge_row: typing.List[str]
                for edge_row in potential_edge_attributes:
                    attribute_number += 1

                    # Generate a new ID that will sort after the new edge.
                    # What if the existing ID is not a symbol or a string?
                    #
                    # TODO: Handle these cases.
                    new_id: str
                    if node1_value.startswith(KgtkFormat.STRING_SIGIL) and node1_value.endsswith(KgtkFormat.STRING_SIGIL):
                        new_id = node1_value[:-1] + "-" + str(attribute_number).zfill(width) + KgtkFormat.STRING_SIGIL
                    else:
                        new_id = node1_value + "-" + str(attribute_number).zfill(width)

                    kw.writemap({
                        node1_column_name: node1_value,
                        label_column_name: edge_row[label_column_idx],
                        node2_column_name: edge_row[node2_column_idx],
                        id_column_name: new_id
                    })
                    output_line_count += 1
                
                    if unreifiedw is not None:
                        unreifiedw.writemap({
                            node1_column_name: node1_value,
                            label_column_name: edge_row[label_column_idx],
                            node2_column_name: edge_row[node2_column_idx],
                            id_column_name: new_id
                        })
                
            else:
                # Unreification was not triggered.  Pass this group of rows
                # through unchanged, except for possibly appending an ID
                # column.
                #
                # TODO: Perhaps we'd like to build an ID value at the same time?
                for row in node1_group:
                    if uninvolvedw is not None:
                        uninvolvedw.write(row)

                    if new_id_column:
                        row = row.copy()
                        row.append("")

                    kw.write(row)
                    output_line_count += 1

        if self.verbose:
            print("Processed %d records in %d groups." % (input_line_count, input_group_count), file=self.error_file, flush=True)
            print("Unreified %d groups." % unreification_count, file=self.error_file, flush=True)
            print("Wrote %d output records" % output_line_count, file=self.error_file, flush=True)

        
        kw.close()
        if reifiedw is not None:
            reifiedw.close()
        if unreifiedw is not None:
            unreifiedw.close()
        if uninvolvedw is not None:
            uninvolvedw.close()

            
def main():
    """
    Test the KGTK copy template.
    """
    parser: ArgumentParser = ArgumentParser()

    parser.add_argument("-i", "--input-file", dest="input_file_path",
                        help="The KGTK input file. (default=%(default)s)", type=Path, default="-")

    parser.add_argument("-o", "--output-file", dest="output_file_path",
                        help="The KGTK output file. (default=%(default)s).", type=Path, default="-")
    
    parser.add_argument(      "--reified-file", dest="reified_file_path",
                              help="A KGTK output file that will contain only the reified RDF statements. (default=%(default)s).", type=Path, default=None)
    
    parser.add_argument(      "--unreified-file", dest="unreified_file_path",
                              help="A KGTK output file that will contain only the unreified RDF statements. (default=%(default)s).", type=Path, default=None)
    
    parser.add_argument(      "--uninvolved-file", dest="uninvolved_file_path",
                              help="A KGTK output file that will contain only the uninvolved input records. (default=%(default)s).", type=Path, default=None)
    
    KgtkReader.add_debug_arguments(parser)
    KgtkReaderOptions.add_arguments(parser, mode_options=False, expert=True)
    KgtkValueOptions.add_arguments(parser)

    args: Namespace = parser.parse_args()

    error_file: typing.TextIO = sys.stdout if args.errors_to_stdout else sys.stderr

    # Build the option structures.                                                                                                                          
    reader_options: KgtkReaderOptions = KgtkReaderOptions.from_args(args)
    value_options: KgtkValueOptions = KgtkValueOptions.from_args(args)

   # Show the final option structures for debugging and documentation.                                                                                             
    if args.show_options:
        print("--input-files %s" % " ".join([str(path) for  path in input_file_paths]), file=error_file, flush=True)
        print("--output-file=%s" % str(args.output_file_path), file=error_file, flush=True)
        if args.reified_file_path is not None:
            print("--reified-file=%s" % str(args.reified_file_path), file=error_file, flush=True)
        if args.unreified_file_path is not None:
            print("--unreified-file=%s" % str(args.unreified_file_path), file=error_file, flush=True)
        if args.uninvolved_file_path is not None:
            print("--uninvolved-file=%s" % str(args.uninvolved_file_path), file=error_file, flush=True)

        reader_options.show(out=error_file)
        value_options.show(out=error_file)

    kurs: KgtkUnreifyRdfStatements = KgtkUnreifyRdfStatements(
        input_file_path=args.input_file_path,
        output_file_path=args.output_file_path,
        reified_file_path=args.reified_file_path,
        unreified_file_path=args.unreified_file_path,
        uninvolved_file_path=args.uninvolved_file_path,
        reader_options=reader_options,
        value_options=value_options,
        error_file=error_file,
        verbose=args.verbose,
        very_verbose=args.very_verbose,
    )

    kurs.process()
    
if __name__ == "__main__":
    main()
