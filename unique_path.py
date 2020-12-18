from pathlib import Path
import string

def get_unique_path(path=None, index=0, qualifiers=None):
    if path.exists():
        # get stem
        failed_index = index
        #failed_qualifier = '_' + str(failed_index)
        index = index + 1
        stem = path.stem
        suffix = path.suffix
        # remove previous qualifier
        #if stem.endswith(failed_qualifier):
        if stem[-2:-1]=='_':
            original_stem = stem[:-2]
            print('original_stem:',original_stem)
            failed_qualifier = stem[-1:]
            print('failed_qualifier:',failed_qualifier)
            failed_qualifier_index = qualifiers.index(failed_qualifier)
            print('failed_qualifier_index:',failed_qualifier_index)
            new_qualifier = qualifiers[failed_qualifier_index+1]
        else:
            # No previous qualifier established
            original_stem = stem
            new_qualifier = qualifiers[0]

        #new_stem = original_stem + '_' + str(index)
        #new_name = stem + '_U' + suffix

        new_name = original_stem + '_' + new_qualifier + suffix
        new_path = Path(new_name)
        # add unique to stem
        return(get_unique_path(path=new_path, index=index, qualifiers=qualifiers))
    else:
        return path

candidate_path = Path('test.txt')
qualifiers = list(string.ascii_uppercase)
#print(qualifiers)
print(candidate_path)
print(get_unique_path(path=candidate_path, qualifiers=qualifiers))