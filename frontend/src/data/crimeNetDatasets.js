// CrimeNet benchmark datasets catalog and loaders
import ds_unbound_case_2026 from './datasets/unbound_case_2026.json';
import ds_911_hijackers from './datasets/911_hijackers.json';
import ds_montreal_gangs from './datasets/montreal_gangs.json';
import ds_madoff from './datasets/madoff.json';
import ds_rhodes_bombing from './datasets/rhodes_bombing.json';
import ds_moreno_crime from './datasets/moreno_crime.json';
import ds_noordintop from './datasets/noordintop.json';
import ds_bbc_islam_groups from './datasets/bbc_islam_groups.json';
import ds_israel_lea_case1 from './datasets/israel_lea_case1.json';
import ds_israel_lea_case2 from './datasets/israel_lea_case2.json';
import ds_csi_s01e07 from './datasets/csi_s01e07.json';
import ds_csi_s01e08 from './datasets/csi_s01e08.json';
import ds_baseball_steroid_use from './datasets/baseball_steroid_use.json';
import ds_nist_c1 from './datasets/nist_c1.json';
import ds_nist_c2 from './datasets/nist_c2.json';

export const DATASETS_CATALOG = [
  {
    id: 'unbound_case_2026',
    name: 'UNBOUND — Indian Criminal Network 2026',
    description: 'Synthetic syndicate case with phones, persons, organizations, locations, and bank accounts',
    data: ds_unbound_case_2026
  },
  {
    id: '911_hijackers',
    name: '911 Hijackers',
    description: 'Covert terrorist network responsible for 9/11 attacks',
    data: ds_911_hijackers
  },
  {
    id: 'montreal_gangs',
    name: 'Montreal Street Gangs',
    description: 'Street gangs in Montreal with co-offending ties',
    data: ds_montreal_gangs
  },
  {
    id: 'madoff',
    name: 'Madoff Frauds',
    description: 'Bernard Madoff Ponzi scheme financial and familial network',
    data: ds_madoff
  },
  {
    id: 'rhodes_bombing',
    name: 'Rhodes Bombing',
    description: 'Rhodes bombing covert network',
    data: ds_rhodes_bombing
  },
  {
    id: 'moreno_crime',
    name: 'Moreno Crime Network',
    description: 'Co-offending network of criminal actors and associates',
    data: ds_moreno_crime
  },
  {
    id: 'noordintop',
    name: 'Noordin Top Network',
    description: 'Noordin Top terrorist network with organizational and familial ties',
    data: ds_noordintop
  },
  {
    id: 'bbc_islam_groups',
    name: 'BBC Islam Groups',
    description: 'Religious and political covert network',
    data: ds_bbc_islam_groups
  },
  {
    id: 'israel_lea_case1',
    name: 'Israel LEA Case 1',
    description: 'Law enforcement intercepted communication case 1',
    data: ds_israel_lea_case1
  },
  {
    id: 'israel_lea_case2',
    name: 'Israel LEA Case 2',
    description: 'Law enforcement intercepted communication case 2',
    data: ds_israel_lea_case2
  },
  {
    id: 'csi_s01e07',
    name: 'CSI (s01e07)',
    description: 'CSI investigation episode 7 forensic evidence network',
    data: ds_csi_s01e07
  },
  {
    id: 'csi_s01e08',
    name: 'CSI (s01e08)',
    description: 'CSI investigation episode 8 forensic evidence network',
    data: ds_csi_s01e08
  },
  {
    id: 'baseball_steroid_use',
    name: 'Baseball Steroid Use',
    description: 'Mitchell Report performance enhancing substance distribution network',
    data: ds_baseball_steroid_use
  },
  {
    id: 'nist_c1',
    name: 'NIST C1',
    description: 'NIST benchmark intelligence case 1',
    data: ds_nist_c1
  },
  {
    id: 'nist_c2',
    name: 'NIST C2',
    description: 'NIST benchmark intelligence case 2',
    data: ds_nist_c2
  },
];

export function getDatasetById(id) {
  const found = DATASETS_CATALOG.find(d => d.id === id);
  return found ? found.data : DATASETS_CATALOG[0].data;
}

export default DATASETS_CATALOG;
