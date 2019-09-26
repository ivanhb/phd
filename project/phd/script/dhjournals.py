from argparse import ArgumentParser
from os.path import exists
from os import makedirs, sep
from journals import Journals

if __name__ == "__main__":
    arg_parser = ArgumentParser("dhjournals.py", description="Handle DH Journals data of Gianmarco's work")
    arg_parser.add_argument("-in", "--input_csv", dest="dh_csv_path", required=True, help="The csv path")
    arg_parser.add_argument("-out", "--output_dir", dest="output_dir", default="", required=False, help="The output directory where you want to store the results")
    arg_parser.add_argument("-s", "--source", dest="source", required=False, default="crossref", help="The source from which you wish to get the journals DOIs")
    arg_parser.add_argument("-l", "--limit", dest="limit", required=False, default="-1", help="A limit number of journal to process")
    arg_parser.add_argument("-o", "--offset", dest="offset", required=False, default="0", help="Starting offset in the journals list")
    arg_parser.add_argument("-r", "--repeat", dest="repeat", required=False, default=False, help="Try again all the calls finished with errors")
    arg_parser.add_argument("-n", "--normalize", dest="normalize_results", required=False, default=False, help="Normalize the csv results obtained")

    args = arg_parser.parse_args()

    NORMALIZE = False
    if args.normalize_results:
        NORMALIZE = True

    REPEAT = False
    if args.repeat:
        REPEAT = True

    journals = Journals(args.dh_csv_path, args.output_dir, "extended_dh_journals.csv")
    if NORMALIZE:
        print("Normalize the results ...")
        #Normalize section
        journals.normalize_results()
    else:
        print("Elaborating journals ...")
        #Processing section
        journals.build_obj_from_csv()
        #SERVICE_CALL = "", LIMIT = -1, PRINT=True, TRY_AGAIN= False
        journals.extend_journals_with_dois(args.source, int(args.limit), True, REPEAT)
