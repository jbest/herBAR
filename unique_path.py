from pathlib import Path
import string
import uuid

def get_unique_path(path=None, qualifiers=None):
    if path.exists():
        print('path exists:', path)
        # get stem
        stem = path.stem
        suffix = path.suffix
        path_parent = path.parent
        # remove previous qualifier
        if stem[-2:-1]=='_':
            original_stem = stem[:-2]
            print('original_stem:',original_stem)
            failed_qualifier = stem[-1:]
            print('failed_qualifier:',failed_qualifier)
            failed_qualifier_index = qualifiers.index(failed_qualifier)
            print('failed_qualifier_index:',failed_qualifier_index)
            try:
                new_qualifier = qualifiers[failed_qualifier_index+1]
            except IndexError:
                # ran out of qualifiers
                # using UUID instead
                new_qualifier = str(uuid.uuid4())
        else:
            # No previous qualifier established
            original_stem = stem
            new_qualifier = qualifiers[0]

        # add unique to stem
        new_name = original_stem + '_' + new_qualifier + suffix
        #new_path = Path(new_name)
        new_path = path_parent / new_name
        
        return(get_unique_path(path=new_path, qualifiers=qualifiers))
    else:
        return path

candidate_path = Path('subpath/test.txt')
#qualifiers = list(string.ascii_uppercase)
#test short list
qualifiers = list('AB')
print(qualifiers)
print(candidate_path)
print(get_unique_path(path=candidate_path, qualifiers=qualifiers))